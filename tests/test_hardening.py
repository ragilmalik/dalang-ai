"""Go-live hardening (2026-11-05): structured logs with request/job ids and no secrets, readiness, the three
server modes (live / fake / not_configured), bundled real sample films, SAM phrase fallbacks, local-disk encodes."""
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import logs, samples
from api.config import settings
from api.main import app

client = TestClient(app)


def test_scrub_removes_credentials():
    text = logs.scrub('Authorization: Bearer abc.DEF-123 api_key="zzz999" token=qq sk-abcdefghijklmnop ok')
    assert "abc.DEF-123" not in text and "zzz999" not in text and "sk-abcdefghijklmnop" not in text
    assert text.endswith("ok") and "[redacted]" in text


def test_request_id_is_echoed_or_made():
    r = client.get("/api/health", headers={"X-Request-ID": "judge-42"})
    assert r.headers["x-request-id"] == "judge-42"
    r = client.get("/api/health", headers={"X-Request-ID": "bad id with spaces"})
    assert r.headers["x-request-id"] != "bad id with spaces" and len(r.headers["x-request-id"]) == 16


def test_json_log_line_carries_ids_and_no_secret(monkeypatch):
    rec = logging.makeLogRecord({"name": "dalang.t", "levelname": "INFO", "levelno": 20,
                                 "msg": "calling with Bearer s3cr3tvalue", "args": None})
    tok_r, tok_j = logs.request_id.set("rid1"), logs.job_id.set("job1")
    try:
        assert logs.ContextFilter().filter(rec)
        line = json.loads(logs.JsonFormatter().format(rec))
    finally:
        logs.request_id.reset(tok_r)
        logs.job_id.reset(tok_j)
    assert line["request_id"] == "rid1" and line["job_id"] == "job1" and "s3cr3tvalue" not in line["msg"]


def test_text_formatter_shows_context():
    rec = logging.makeLogRecord({"name": "x", "levelname": "INFO", "levelno": 20, "msg": "hi", "args": None,
                                 "request_id": "r9", "job_id": "j9"})
    assert "[rid=r9 job=j9]" in logs.TextFormatter().format(rec)


def test_health_reports_fake_mode_in_tests():
    h = client.get("/api/health").json()
    assert h["mode"] == "fake" and h["live"] is False and h["fake_meta"] is True


def test_not_configured_refuses_new_films_but_serves_gallery(monkeypatch):
    monkeypatch.setattr(settings, "fake_flag", False)
    monkeypatch.setattr(settings, "meta_api_key", "")
    assert settings.mode == "not_configured"
    r = client.post("/api/jobs", data={"text": "Dulu ada kancil.", "review": "false"})
    assert r.status_code == 503 and "no Meta Model API key" in r.json()["detail"]
    assert client.get("/api/gallery").status_code == 200
    rd = client.get("/api/ready")
    assert rd.status_code == 503 and rd.json()["mode"] == "not_configured" and rd.json()["ready"] is False


def test_ready_in_fake_mode():
    r = client.get("/api/ready")
    assert r.status_code == 200 and r.json()["ready"] is True and "meta_api" not in r.json()


def test_ready_live_checks_models(monkeypatch):
    from api import main

    monkeypatch.setattr(settings, "fake_flag", False)
    monkeypatch.setattr(settings, "meta_api_key", "k")
    monkeypatch.setattr(main, "_models_reachable", lambda: {"reachable": True, "status": 200, "missing": []})
    r = client.get("/api/ready")
    assert r.status_code == 200 and r.json()["meta_api"]["reachable"] is True
    monkeypatch.setattr(main, "_models_reachable", lambda: {"reachable": True, "status": 200, "missing": ["sam-3.1"]})
    assert client.get("/api/ready").status_code == 503


def test_import_bundled_copies_once(tmp_path, monkeypatch):
    jid = "bundleTest1"
    src = tmp_path / "kancil-id"
    (src / "puppets").mkdir(parents=True)
    (src / "poster.jpg").write_bytes(b"jpg")
    (src / "puppets" / "kancil.png").write_bytes(b"png")
    (src / "state.json").write_text(json.dumps({"id": jid, "status": "done", "sample": True, "sample_key": "kancil-id",
                                                "created": 1.0, "title": "T", "public": True}))
    assert [s["id"] for s in samples.bundled(tmp_path)] == [jid]
    assert samples.import_bundled(tmp_path) == [jid]
    assert (settings.data_dir / "jobs" / jid / "puppets" / "kancil.png").exists()
    assert not (settings.data_dir / "jobs" / jid / "state.json").exists()
    assert samples.import_bundled(tmp_path) == []  # once only
    assert any(g["id"] == jid for g in client.get("/api/gallery").json())


def test_shipped_samples_are_real_and_labelled():
    shipped = samples.bundled()
    if not shipped:
        pytest.skip("no bundled samples in this checkout")
    for s in shipped:
        assert s["sample"] and s["bundled"] and s["offline"] is False and "written for this project" in s["sample_note"]
        folder = samples.BUNDLE / s["sample_key"]
        assert (folder / "dalang_landscape.mp4").exists() and (folder / "poster.jpg").exists()
        assert not any(sc.get("placeholder") for sc in s.get("scenes", []))


def test_sam_phrase_fallbacks():
    from api.pipeline import segment

    assert segment.queries("mouse deer puppet") == ["mouse deer puppet", "mouse deer", "deer", "puppet"]
    assert segment.queries("puppet") == ["puppet"]
    assert segment.queries("wayang giant") == ["wayang giant", "giant", "puppet"]
    assert segment.queries("golden snail princess") == ["golden snail princess", "princess", "puppet"]
    assert segment.queries("golden snail princess", "human") == ["golden snail princess", "princess", "person", "puppet"]
    assert segment.queries("giant puppet", "creature")[-2:] == ["creature", "puppet"]


def test_staged_encode_moves_file(tmp_path, monkeypatch):
    from api.pipeline import media

    out = tmp_path / "film.mp4"
    monkeypatch.setenv("ENCODE_DIR", str(tmp_path / "enc"))
    with media.staged(out) as dst:
        assert dst != out and Path(dst).parent == tmp_path / "enc"
        Path(dst).write_bytes(b"x")
    assert out.read_bytes() == b"x" and not list((tmp_path / "enc").iterdir())
    monkeypatch.delenv("ENCODE_DIR")
    with media.staged(out) as dst:
        assert dst == out


def test_empty_model_reply_retries_with_less_reasoning(monkeypatch):
    from api import meta_client

    calls = []

    class R:
        def __init__(self, content):
            self._c = content

        def json(self):
            return {"choices": [{"message": {"content": self._c}, "finish_reason": "length"}], "usage": {}}

    def post(url, **kw):
        calls.append(kw["json"]["reasoning_effort"])
        return R(None if len(calls) == 1 else '{"ok": true}')

    monkeypatch.setattr(meta_client, "_post", post)
    out = meta_client.chat_json([{"role": "user", "content": "x"}], {"type": "object"}, "t", model="muse-spark-1.3")
    assert out == {"ok": True} and calls == ["medium", "low"]
    calls.clear()
    monkeypatch.setattr(meta_client, "_post", lambda url, **kw: (calls.append(1), R(None))[1])
    with pytest.raises(meta_client.MetaAPIError):
        meta_client.chat_json([{"role": "user", "content": "x"}], {"type": "object"}, "t", model="muse-spark-1.3")
