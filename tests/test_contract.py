"""Contract tests: every request meta_client builds is checked against the documented request shapes
(api/contract.py, from dev.meta.ai), and every reply the fake API gives against the documented response shapes.
If one of these fails, the real API would most likely answer 400 on go-live day."""
import json
import math
import struct
import wave
from pathlib import Path

import httpx
import pytest

from api import contract, cost, fake_meta, meta_client, runner
from api.config import settings
from api.jobs import Job
from api.pipeline import mock

SEEN: list[tuple[str, list[str], list[str]]] = []  # (path, request violations, response violations)


class Capture(httpx.BaseTransport):
    def __init__(self) -> None:
        self.inner = fake_meta.transport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        req_errs = contract.check_request(request.method, str(request.url), dict(request.headers), request.content)
        resp = self.inner.handle_request(request)
        raw = resp.read()
        resp_errs: list[str] = []
        if "json" in resp.headers.get("content-type", ""):
            resp_errs = contract.check_response(request.url.path, resp.status_code, json.loads(raw))
        SEEN.append((request.url.path, req_errs, resp_errs))
        return httpx.Response(resp.status_code, headers=resp.headers, content=raw, request=request)


@pytest.fixture
def capture(monkeypatch):
    SEEN.clear()
    monkeypatch.setattr(meta_client, "_clients", {settings.fake_meta: httpx.Client(transport=Capture())})
    m = cost.Meter(10.0)
    cost.use(m)
    yield SEEN
    cost.use(None)


def _wav(path: Path, seconds: float = 1.5, sr: int = 16000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(i / 7))) for i in range(int(sr * seconds))))
    return path


def _clean(seen):
    bad = [(p, r, s) for p, r, s in seen if r or s]
    assert not bad, bad


def test_a_whole_film_sends_only_documented_requests(capture):
    import shutil

    shutil.rmtree(settings.data_dir / "cache", ignore_errors=True)  # no cached script or art: every call goes out
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " contract")
    assert job.s["status"] == "review", job.s.get("error")
    runner._back(job)
    assert job.s["status"] == "done", job.s.get("error")
    paths = {p for p, _, _ in capture}
    assert {"/v1/chat/completions", "/v1/images/generations", "/v1/responses"} <= paths
    assert len(capture) >= 20
    _clean(capture)


def test_listen_requests_match_the_docs(capture, tmp_path):
    wav = _wav(tmp_path / "s.wav")
    meta_client.transcribe_turns(wav, 1.5, ["Indonesian", "English"], ["kancil", "wayang"])
    meta_client.transcribe_with_spark_audio(wav, "Javanese")
    assert [p for p, _, _ in capture] == ["/v1/asr/transcribe", "/v1/chat/completions"]
    _clean(capture)


def test_edit_and_open_weight_requests_match_the_docs(capture, tmp_path, monkeypatch):
    ref = mock.puppet(tmp_path / "p.png", "Kancil", "animal", 1)
    meta_client.edit_image("same puppet, waving", [ref], tmp_path / "e.png")
    monkeypatch.setattr(settings, "baseten_api_key", "k")
    meta_client.chat_json([{"role": "user", "content": "STORY (code 'id')"}], {"type": "object"}, "lakon",
                          open_weights=True)
    meta_client.chat_json([{"role": "user", "content": "Title: A\nMoral: B"}], {"type": "object"}, "polish",
                          glimmer=True)
    hosts = len(capture)
    assert hosts == 3
    _clean(capture)


@pytest.mark.parametrize("body,needle", [
    ({"model": "muse-image-1.0", "prompt": "x", "seed": 3}, "unknown top-level field 'seed'"),
    ({"model": "muse-image-1.0", "prompt": "x", "n": 11}, "n must be 1..10"),
    ({"model": "muse-image-1.0", "prompt": "x", "size": "4000x100"}, "aspect"),
    ({"model": "muse-image-1.0", "prompt": ""}, "prompt"),
    ({"model": "muse-image-1.0", "prompt": "x", "tool_enablement": {"web_search": False}}, "tool_enablement"),
])
def test_contract_catches_bad_image_requests(body, needle):
    errs = contract.check_request("POST", "https://api.meta.ai/v1/images/generations",
                                  {"Authorization": "Bearer k"}, json.dumps(body).encode())
    assert any(needle in e for e in errs), errs


def test_contract_catches_bad_chat_sam_and_edit_requests():
    bad_audio = {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": [
        {"type": "input_audio", "input_audio": {"data": "AAA", "format": "wav"}}]}]}
    errs = contract.check_request("POST", "https://api.meta.ai/v1/chat/completions", {"Authorization": "Bearer k"},
                                  json.dumps(bad_audio).encode())
    assert any("muse-spark-1.2" in e for e in errs) and any("max_tokens" in e for e in errs)
    errs = contract.check_request("POST", "https://api.meta.ai/v1/responses", {}, json.dumps(
        {"model": "sam-3.1", "stream": False, "metadata": {"include_confidence": True}, "input": []}).encode())
    assert len(errs) >= 4  # no bearer, not streamed, non-string metadata, bad input
    errs = contract.check_request("POST", "https://api.meta.ai/v1/images/edits", {"Authorization": "Bearer k"},
                                  json.dumps({"model": "muse-image-1.0", "prompt": "x",
                                              "images": [{"image_url": "u", "file_id": "f"}]}).encode())
    assert any("exactly one" in e for e in errs)
    errs = contract.check_request("POST", "https://api.together.xyz/v1/chat/completions", {}, json.dumps(
        {"model": "glimmer", "temperature": 0, "messages": [{"role": "user", "content": "x"}]}).encode())
    assert any("Glimmer" in e for e in errs) and any("temperature" in e for e in errs)
    assert contract.check_request("POST", "https://api.meta.ai/v1/videos", {"Authorization": "Bearer k"}, b"{}")


def test_contract_checks_response_shapes():
    assert contract.check_response("/v1/images/generations", 200, {"data": []})
    assert contract.check_response("/v1/chat/completions", 200, {"choices": []})
    assert contract.check_response("/v1/asr/transcribe", 200, {"transcript": "x", "turns": [{"startMs": 1}]})
    assert contract.check_response("/v1/x", 503, {"oops": 1})
    assert not contract.check_response("/v1/x", 400, {"error": {"message": "bad"}})
    assert not contract.check_response("/v1/asr/transcribe", 200, {"transcript": "x", "turns": []})
