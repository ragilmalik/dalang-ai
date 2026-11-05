"""Narration fallbacks and ffmpeg helpers (media.py) plus the error branches of meta_client."""
import json
import subprocess
import sys

import httpx
import numpy as np
import pytest

from api import cost, meta_client
from api.config import settings
from api.pipeline import media

# ----------------------------------------------------------------------------- media.py


def test_wav_roundtrip_and_seconds(tmp_path):
    p = tmp_path / "a.wav"
    samples = np.sin(np.linspace(0, 100, media.SR)).astype(np.float32) * 0.5
    media.write_wav(p, samples)
    back = media.read_wav(p)
    assert len(back) == media.SR
    assert np.max(np.abs(back - samples)) < 1e-3
    assert media.wav_seconds(p) == pytest.approx(1.0)


def test_write_wav_clips_loud_samples(tmp_path):
    p = tmp_path / "loud.wav"
    media.write_wav(p, np.array([5.0, -5.0, 0.0], dtype=np.float32))
    back = media.read_wav(p)
    assert back[0] == pytest.approx(1.0, abs=1e-3) and back[1] == pytest.approx(-1.0, abs=1e-3)


def test_to_wav_converts_and_trims(tmp_path):
    src = tmp_path / "long.wav"
    media.write_wav(src, np.zeros(media.SR * 3, dtype=np.float32), sr=media.SR)
    out = media.to_wav(src, tmp_path / "short.wav", sr=16000, max_seconds=1)
    assert media.wav_seconds(out) == pytest.approx(1.0, abs=0.05)
    import wave
    with wave.open(str(out), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2


def test_run_reports_ffmpeg_failure(tmp_path):
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        media.run(["-i", str(tmp_path / "missing.wav"), str(tmp_path / "o.wav")])


def test_ffmpeg_exe_prefers_system_binary(monkeypatch):
    monkeypatch.setattr(media.shutil, "which", lambda name: "/usr/bin/ffmpeg-test")
    assert media.ffmpeg_exe() == "/usr/bin/ffmpeg-test"


def test_voices_cover_every_story_language():
    from api import tts

    assert set(tts.EDGE) == {"id", "jv", "en"}
    assert tts.EDGE["jv"].voice.startswith("jv-ID")


def _fake_edge(monkeypatch, tmp_path, *, fail: bool):
    """Replace edge_tts.Communicate with a stub that writes a real mp3-less silent wav as 'mp3' (ffmpeg sniffs it)."""
    import edge_tts

    seen = {}

    class Comm:
        def __init__(self, text, voice, rate=None, pitch=None):
            seen.update(text=text, voice=voice, rate=rate)

        async def save(self, path):
            if fail:
                raise ConnectionError("proxy said no")
            media.write_wav(tmp_path / "stub.wav", np.zeros(2400, dtype=np.float32))
            (tmp_path / "stub.wav").replace(path)

    monkeypatch.setattr(edge_tts, "Communicate", Comm)
    return seen


def test_narrate_uses_language_voice_and_slows_down(monkeypatch, tmp_path):
    from api import tts

    monkeypatch.setenv("TTS_ENGINE", "edge")
    seen = _fake_edge(monkeypatch, tmp_path, fail=False)
    out = media.narrate("Halo", "jv", tmp_path / "n.wav")
    assert out == tmp_path / "n.wav" and out.exists()
    assert seen["voice"] == tts.EDGE["jv"].voice and seen["rate"] == tts.EDGE["jv"].rate


def test_narrate_unknown_language_falls_back_to_indonesian(monkeypatch, tmp_path):
    from api import tts

    monkeypatch.setenv("TTS_ENGINE", "edge")
    seen = _fake_edge(monkeypatch, tmp_path, fail=False)
    assert media.narrate("Halo", "xx", tmp_path / "n.wav") is not None
    assert seen["voice"] == tts.EDGE["id"].voice


def test_narrate_retries_in_subprocess_without_proxy(monkeypatch, tmp_path):
    _fake_edge(monkeypatch, tmp_path, fail=True)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        media.write_wav(tmp_path / "n.mp3", np.zeros(2400, dtype=np.float32))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    from api import tts

    monkeypatch.setenv("TTS_ENGINE", "edge")
    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    out = media.narrate("Halo", "en", tmp_path / "n.wav")
    assert out is not None
    cmd, kw = calls[0]
    assert cmd[:3] == [sys.executable, "-m", "edge_tts"] and "--voice" in cmd
    assert not any("proxy" in k.lower() for k in kw["env"])  # proxy settings removed for the retry


def test_narrate_gives_up_quietly_when_voice_is_unreachable(monkeypatch, tmp_path):
    from api import tts

    monkeypatch.setenv("TTS_ENGINE", "edge")
    _fake_edge(monkeypatch, tmp_path, fail=True)
    monkeypatch.setattr(tts.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "offline"))
    assert media.narrate("Halo", "id", tmp_path / "n.wav") is None


def test_narrate_returns_none_when_audio_cannot_be_decoded(monkeypatch, tmp_path):
    from api import tts

    monkeypatch.setenv("TTS_ENGINE", "edge")
    _fake_edge(monkeypatch, tmp_path, fail=False)

    def boom(*a, **k):
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr(tts, "finish", boom)
    assert media.narrate("Halo", "id", tmp_path / "n.wav") is None


def test_gong_and_bonang_are_bounded_audio():
    g = media.gong(1.0)
    b = media.bonang(media.SLENDRO[0], 0.5)
    assert len(g) == media.SR and len(b) == media.SR // 2
    assert g.dtype == np.float32 and np.max(np.abs(g)) < 1.0 and np.max(np.abs(b)) < 1.0
    assert np.max(np.abs(g)) > 0.05  # audible


# ----------------------------------------------------------------------------- meta_client.py


@pytest.fixture
def meter():
    m = cost.Meter(5.0)
    cost.use(m)
    yield m
    cost.use(None)


@pytest.fixture
def no_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr(meta_client.time, "sleep", lambda s: waits.append(s))
    return waits


def _client_with(monkeypatch, handler):
    monkeypatch.setattr(meta_client, "_clients", {settings.fake_meta: httpx.Client(transport=httpx.MockTransport(handler))})


def test_post_retries_rate_limits_with_backoff_then_succeeds(monkeypatch, no_sleep, meter):
    codes = iter([429, 503, 200])

    def handler(req):
        c = next(codes)
        return httpx.Response(c, json={"ok": True})

    _client_with(monkeypatch, handler)
    r = meta_client._post("https://api.meta.ai/v1/chat/completions", json={"model": "muse-spark-1.3"})
    assert r.status_code == 200
    assert len(no_sleep) == 2 and 2 <= no_sleep[0] <= 2.5 and 4 <= no_sleep[1] <= 5  # exponential back-off + jitter


def test_post_client_error_is_not_retried(monkeypatch, no_sleep, meter):
    n = []

    def handler(req):
        n.append(1)
        return httpx.Response(400, text="bad field " * 200)

    _client_with(monkeypatch, handler)
    with pytest.raises(meta_client.MetaAPIError) as e:
        meta_client._post("https://api.meta.ai/v1/x", json={})
    assert len(n) == 1 and no_sleep == []
    assert "400" in str(e.value) and len(str(e.value)) < 800  # body trimmed


def test_post_gives_up_after_retries_on_server_errors(monkeypatch, no_sleep, meter):
    _client_with(monkeypatch, lambda req: httpx.Response(500, text="down"))
    with pytest.raises(meta_client.MetaAPIError, match="500"):
        meta_client._post("https://api.meta.ai/v1/x", json={}, retries=2)
    assert len(no_sleep) == 2


def test_post_survives_a_timeout_and_reports_when_it_persists(monkeypatch, no_sleep, meter):
    state = {"n": 0}

    def flaky(req):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ReadTimeout("slow", request=req)
        return httpx.Response(200, json={})

    _client_with(monkeypatch, flaky)
    assert meta_client._post("https://api.meta.ai/v1/x", json={}).status_code == 200

    def dead(req):
        raise httpx.ConnectError("no route", request=req)

    _client_with(monkeypatch, dead)
    with pytest.raises(meta_client.MetaAPIError, match="failed"):
        meta_client._post("https://api.meta.ai/v1/x", json={}, retries=1)


def test_failed_calls_land_in_the_trace(monkeypatch, no_sleep, meter):
    _client_with(monkeypatch, lambda req: httpx.Response(401, text="no"))
    with pytest.raises(meta_client.MetaAPIError):
        meta_client._post("https://api.meta.ai/v1/chat/completions", json={"model": "muse-spark-1.3"}, purpose="test call")
    last = meter.trace[-1]
    assert last["ok"] is False and last["error"] == "HTTP 401" and last["model"] == "muse-spark-1.3"
    assert last["purpose"] == "test call" and last["endpoint"] == "/v1/chat/completions"


def test_endpoint_and_model_helpers():
    assert meta_client._endpoint("https://api.meta.ai/v1/images/generations?x=1") == "/v1/images/generations"
    assert meta_client._endpoint("nohost") == "nohost"
    assert meta_client._model_of({"json": {"model": "m1"}}) == "m1"
    req = json.dumps({"model": "muse-voice"})
    assert meta_client._model_of({"files": {"request": (None, req, "application/json")}}) == "muse-voice"
    assert meta_client._model_of({"files": {"request": (None, "{not json", "application/json")}}) == "?"
    assert meta_client._model_of({}) == "?"


def test_key_helper_uses_placeholder_only_for_the_fake_api(monkeypatch):
    assert meta_client._key("real") == "real"
    assert meta_client._key("") == "fake-key"  # tests run with FAKE_META=1
    monkeypatch.setattr(type(settings), "fake_meta", property(lambda self: False))
    assert meta_client._key("") == ""


@pytest.mark.parametrize("text,expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('Sure! Here it is: {"a": [1, 2]} hope it helps', {"a": [1, 2]}),
    ('[1, 2, 3]', [1, 2, 3]),
])
def test_extract_json_tolerates_fences_and_chatter(text, expected):
    assert meta_client._extract_json(text) == expected


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        meta_client._extract_json("no json here at all")


def test_image_bytes_branches():
    import base64
    ok = httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(b"PNGDATA").decode()}]})
    assert meta_client._image_bytes(ok) == b"PNGDATA"
    with pytest.raises(meta_client.MetaAPIError, match="no image"):
        meta_client._image_bytes(httpx.Response(200, json={"data": []}))
    with pytest.raises(meta_client.MetaAPIError, match="neither"):
        meta_client._image_bytes(httpx.Response(200, json={"data": [{}]}))


def test_image_bytes_downloads_when_given_a_url(monkeypatch):
    def handler(req):
        return httpx.Response(200, content=b"FROMURL")

    _client_with(monkeypatch, handler)
    r = httpx.Response(200, json={"data": [{"url": "https://cdn.example/x.png"}]})
    assert meta_client._image_bytes(r) == b"FROMURL"


def test_transcribe_turns_skips_malformed_turns(monkeypatch, tmp_path, meter):
    w = tmp_path / "t.wav"
    media.write_wav(w, np.zeros(1600, dtype=np.float32), sr=16000)
    payload = {"transcript": "  halo kancil ", "turns": [
        {"startMs": 0, "endMs": 900, "transcript": " halo "},
        {"startMs": 900, "endMs": 900, "transcript": "zero length"},
        {"startMs": "x", "endMs": 5},
        {"endMs": 5},
        {"startMs": 1000, "endMs": 2000},
    ]}
    _client_with(monkeypatch, lambda req: httpx.Response(200, json=payload))
    text, turns = meta_client.transcribe_turns(w, 1.0, ["Indonesian"], ["Kancil"])
    assert text == "halo kancil"
    assert turns == [{"start_ms": 0, "end_ms": 900, "text": "halo"}, {"start_ms": 1000, "end_ms": 2000, "text": ""}]
    assert meter.spent > 0


def test_transcribe_sends_language_bias_and_keywords(monkeypatch, tmp_path, meter):
    w = tmp_path / "t.wav"
    media.write_wav(w, np.zeros(1600, dtype=np.float32), sr=16000)
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"transcript": "x"})

    _client_with(monkeypatch, handler)
    meta_client.transcribe(w, 1.0, ["Indonesian", "English"], ["Kancil"])
    body = seen[0].content.decode("latin-1")
    assert "languageBias" in body and "Indonesian" in body and "keywords" in body and "ENDPOINTING" in body
    assert "sessionId=dalang-" in str(seen[0].url)


def test_transcribe_without_hints_omits_optional_fields(monkeypatch, tmp_path, meter):
    w = tmp_path / "t.wav"
    media.write_wav(w, np.zeros(1600, dtype=np.float32), sr=16000)
    seen = []
    _client_with(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json={}))[1])
    assert meta_client.transcribe(w, 1.0) == ""
    body = seen[0].content.decode("latin-1")
    assert "languageBias" not in body and "keywords" not in body


def test_spark_audio_transcription_sends_input_audio(monkeypatch, tmp_path, meter):
    w = tmp_path / "jv.wav"
    media.write_wav(w, np.zeros(1600, dtype=np.float32), sr=16000)
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": " Ing alas ana kancil "}}],
                                         "usage": {"prompt_tokens": 100, "completion_tokens": 20}})

    _client_with(monkeypatch, handler)
    assert meta_client.transcribe_with_spark_audio(w, "Javanese") == "Ing alas ana kancil"
    part = seen[0]["messages"][0]["content"][1]
    assert part["type"] == "input_audio" and part["input_audio"]["format"] == "wav"
    assert seen[0]["max_tokens"] >= 4000 and "Javanese" in seen[0]["messages"][0]["content"][0]["text"]
    assert meter.spent > 0


def _chat_reply(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}], "usage": {}})


def test_open_weights_falls_back_to_json_object_when_schema_rejected(monkeypatch, no_sleep, meter):
    bodies = []

    def handler(req):
        b = json.loads(req.content)
        bodies.append((str(req.url), b))
        if b["response_format"]["type"] == "json_schema":
            return httpx.Response(400, text="response_format json_schema unsupported")
        return _chat_reply('{"ok": true}')

    _client_with(monkeypatch, handler)
    out = meta_client.chat_json([{"role": "user", "content": "x"}], {"type": "object"}, "lakon", open_weights=True)
    assert out == {"ok": True}
    assert [b["response_format"]["type"] for _, b in bodies] == ["json_schema", "json_object"]
    assert bodies[0][1]["model"] == settings.open_model and bodies[0][1]["max_tokens"] == 16384


def test_open_weights_unrelated_errors_are_not_masked(monkeypatch, no_sleep, meter):
    _client_with(monkeypatch, lambda req: httpx.Response(401, text="bad key"))
    with pytest.raises(meta_client.MetaAPIError, match="401"):
        meta_client.chat_json([{"role": "user", "content": "x"}], {"type": "object"}, "lakon", open_weights=True)


def test_open_weights_clamps_unknown_reasoning_effort(monkeypatch, meter):
    seen = []
    _client_with(monkeypatch, lambda req: (seen.append(json.loads(req.content)), _chat_reply("{}"))[1])
    meta_client.chat_json([{"role": "user", "content": "x"}], {}, "lakon", open_weights=True, reasoning_effort="extreme")
    assert seen[0]["reasoning_effort"] == "medium"


def test_open_weights_are_not_billed_to_the_meta_meter(monkeypatch, meter):
    _client_with(monkeypatch, lambda req: httpx.Response(
        200, json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 10**6, "completion_tokens": 10**6}}))
    before = meter.spent
    meta_client.chat_json([{"role": "user", "content": "x"}], {}, "lakon", open_weights=True)
    assert meter.spent == before


def test_glimmer_never_sends_reasoning_effort_and_has_headroom(monkeypatch, meter):
    seen = []
    _client_with(monkeypatch, lambda req: (seen.append((str(req.url), json.loads(req.content))), _chat_reply('```json\n{"a": 1}\n```'))[1])
    out = meta_client.chat_json([{"role": "user", "content": "x"}], {}, "lakon", glimmer=True)
    url, body = seen[0]
    assert out == {"a": 1}
    assert url.startswith(settings.glimmer_api_base) and body["model"] == settings.glimmer_model
    assert "reasoning_effort" not in body and "temperature" not in body and body["max_tokens"] >= 8192


def test_glimmer_falls_back_to_json_object(monkeypatch, no_sleep, meter):
    kinds = []

    def handler(req):
        b = json.loads(req.content)
        kinds.append(b["response_format"]["type"])
        if b["response_format"]["type"] == "json_schema":
            return httpx.Response(422, text="json_schema not supported")
        return _chat_reply('{"b": 2}')

    _client_with(monkeypatch, handler)
    assert meta_client.chat_json([{"role": "user", "content": "x"}], {}, "lakon", glimmer=True) == {"b": 2}
    assert kinds == ["json_schema", "json_object"]


def test_empty_model_reply_is_an_error_not_a_crash_loop(monkeypatch, meter):
    _client_with(monkeypatch, lambda req: _chat_reply(None))
    with pytest.raises(ValueError):
        meta_client.chat_json([{"role": "user", "content": "x"}], {}, "lakon")


def test_purpose_defaults_come_from_schema_name(monkeypatch, meter):
    assert meta_client.PURPOSES["verdict"] == "vision check against the script"
    assert "gara_gara" in meta_client.PURPOSES


def test_generate_image_stops_when_budget_is_gone(tmp_path):
    m = cost.Meter(0.0)
    cost.use(m)
    try:
        with pytest.raises(cost.BudgetExceeded):
            meta_client.generate_image("x", tmp_path / "x.png")
        assert not (tmp_path / "x.png").exists()
    finally:
        cost.use(None)


def test_edit_image_sends_at_most_ten_references(monkeypatch, tmp_path, meter):
    import base64

    from PIL import Image
    refs = []
    for i in range(12):
        p = tmp_path / f"r{i}.png"
        Image.new("RGB", (8, 8), (i, 0, 0)).save(p)
        refs.append(p)
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(b"x").decode()}]})

    _client_with(monkeypatch, handler)
    out = meta_client.edit_image("redo", refs, tmp_path / "o.png", fast=True)
    assert out.read_bytes() == b"x"
    assert len(seen[0]["images"]) == 10 and seen[0]["reasoning_strength"] == "low"
    assert seen[0]["images"][0]["image_url"].startswith("data:image/png;base64,")


def test_data_url_mime_by_extension(tmp_path):
    for name, mime in [("a.jpg", "image/jpeg"), ("a.webp", "image/webp"), ("a.bin", "image/png")]:
        p = tmp_path / name
        p.write_bytes(b"\x00")
        assert meta_client.data_url(p).startswith(f"data:{mime};base64,")


def test_image_part_flattens_transparency_onto_grey(tmp_path):
    from PIL import Image
    im = Image.new("RGBA", (2000, 1000), (0, 0, 0, 0))
    p = tmp_path / "t.png"
    im.save(p)
    part = meta_client.image_part(p, max_side=256)
    assert part["type"] == "image_url" and part["image_url"]["url"].startswith("data:image/jpeg;base64,")
    import base64
    import io
    jpg = Image.open(io.BytesIO(base64.b64decode(part["image_url"]["url"].split(",", 1)[1])))
    assert max(jpg.size) == 256
    r, g, b = jpg.getpixel((10, 10))
    assert abs(r - 128) < 6 and abs(g - 128) < 6 and abs(b - 128) < 6


def test_segment_http_error_raises_and_traces(monkeypatch, tmp_path, no_sleep, meter):
    from PIL import Image
    p = tmp_path / "s.png"
    Image.new("RGB", (16, 16)).save(p)
    _client_with(monkeypatch, lambda req: httpx.Response(400, text="bad sam request"))
    with pytest.raises(meta_client.MetaAPIError, match="SAM 400"):
        meta_client.segment(p, "puppet")


def test_segment_retries_a_busy_server(monkeypatch, tmp_path, no_sleep, meter):
    from PIL import Image
    p = tmp_path / "s.png"
    Image.new("RGB", (16, 16)).save(p)
    n = []

    def handler(req):
        n.append(1)
        return httpx.Response(503, text="busy")

    _client_with(monkeypatch, handler)
    with pytest.raises(meta_client.MetaAPIError):
        meta_client.segment(p, "puppet")
    assert len(n) == 3 and len(no_sleep) == 2 and 2 <= no_sleep[0] <= 2.5 and 4 <= no_sleep[1] <= 5  # back-off + jitter
