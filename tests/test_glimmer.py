"""Muse Glimmer (open weights) for the safety screen and the title/moral polish when USE_OPEN_WEIGHTS=true."""
import json

import httpx
import pytest

from api import fake_meta, meta_client
from api.config import settings
from api.jobs import Job
from api.pipeline import lakon, listen, mock
from api.schemas import Script


@pytest.fixture()
def glimmer_on(monkeypatch):
    monkeypatch.setattr(settings, "use_open_weights", True)
    monkeypatch.setattr(settings, "glimmer_api_key", "test-together")
    seen: list[httpx.Request] = []
    real = fake_meta.handler

    def spy(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return real(req)

    monkeypatch.setattr(fake_meta, "handler", spy)
    meta_client._clients.clear()
    monkeypatch.setattr(meta_client, "client", lambda: httpx.Client(transport=httpx.MockTransport(spy)))
    yield seen
    meta_client._clients.clear()


def test_glimmer_request_follows_the_documented_shape(glimmer_on):
    out = meta_client.chat_json([{"role": "user", "content": "ok?"}],
                                {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                                "ping", glimmer=True)
    assert out == {"ok": True}
    req = glimmer_on[-1]
    body = json.loads(req.content)
    assert str(req.url) == "https://api.together.xyz/v1/chat/completions"
    assert body["model"] == "meta-models/Muse-Glimmer-30B"
    assert "temperature" not in body and "reasoning_effort" not in body and body["max_tokens"] >= 4096
    assert req.headers["authorization"] == "Bearer test-together"


def test_safety_screen_runs_on_glimmer(glimmer_on):
    job = Job.create("id", "classic", False)
    listen.screen(job, mock.SAMPLE_TRANSCRIPT, "x")
    assert "meta-models/Muse-Glimmer-30B" in job.s["models"]
    with pytest.raises(listen.Blocked):
        listen.screen(job, "cerita perang dengan bom", "x")
    assert all(r.url.host == "api.together.xyz" for r in glimmer_on)


def test_polish_on_glimmer_updates_title_and_moral(glimmer_on):
    job = Job.create("id", "classic", False)
    s = lakon.polish(job, Script(**mock.SAMPLE_SCRIPT))
    assert s.title.startswith(mock.SAMPLE_SCRIPT["title"]) and s.title != mock.SAMPLE_SCRIPT["title"]
    assert job.s["polished_by"] == "meta-models/Muse-Glimmer-30B"


def test_polish_skipped_without_open_weights():
    job = Job.create("id", "classic", False)
    s = lakon.polish(job, Script(**mock.SAMPLE_SCRIPT))
    assert s.title == mock.SAMPLE_SCRIPT["title"] and "polished_by" not in job.s


def test_local_glimmer_server_needs_no_key(monkeypatch):
    monkeypatch.setattr(settings, "use_open_weights", True)
    monkeypatch.setattr(settings, "glimmer_api_key", "")
    monkeypatch.setattr(settings, "fake_flag", False)
    monkeypatch.setattr(settings, "meta_api_key", "k")
    monkeypatch.setattr(settings, "glimmer_api_base", "https://api.together.xyz/v1")
    assert not settings.glimmer_active
    monkeypatch.setattr(settings, "glimmer_api_base", "http://localhost:8000/v1")
    assert settings.glimmer_active


def test_health_lists_open_weights_models(monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import app

    monkeypatch.setattr(settings, "use_open_weights", True)
    h = TestClient(app).get("/api/health").json()
    assert "meta-models/Muse-Glimmer-30B" in h["open_weights_models"] and h["models"]["polish"]
