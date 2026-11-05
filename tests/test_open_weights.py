"""Best Open Weight route: USE_OPEN_WEIGHTS=true sends the lakon to Muse Spark Open on Baseten (documented base URL
and model string, from ../work/NOTES-verified-meta-api-2026-10-30.md and docs/OPEN_WEIGHTS.md), on the fake API."""
import json
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from api import fake_meta, meta_client
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import lakon, mock

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def spark_open(monkeypatch):
    monkeypatch.setattr(settings, "use_open_weights", True)
    seen: list[httpx.Request] = []
    real = fake_meta.handler

    def spy(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return real(req)

    meta_client._clients.clear()
    monkeypatch.setattr(meta_client, "client", lambda: httpx.Client(transport=httpx.MockTransport(spy)))
    yield seen
    meta_client._clients.clear()


def test_lakon_goes_to_muse_spark_open_on_baseten(spark_open):
    job = Job.create("en", "classic", review=True)
    script = lakon.run(job, mock.SAMPLE_TRANSCRIPT_SNAIL_EN + f" ({uuid.uuid4().hex})")  # fresh text: no cache hit
    req = next(r for r in spark_open if r.url.host == "inference.baseten.co")
    body = json.loads(req.content)
    assert str(req.url) == "https://inference.baseten.co/v1/chat/completions"
    assert body["model"] == "meta-models/muse-spark-open"
    assert body["response_format"]["type"] == "json_schema" and body["response_format"]["json_schema"]["name"] == "lakon"
    assert body["max_tokens"] == 16384 and body["reasoning_effort"] in {"low", "medium", "high", "xhigh"}
    assert script.title == "The Golden Snail"
    assert "meta-models/muse-spark-open" in job.s["models"]
    assert not any(r.url.host == "api.meta.ai" and b'"name": "lakon"' in r.content for r in spark_open)


def test_unknown_open_model_is_refused_by_the_fake(spark_open, monkeypatch):
    monkeypatch.setattr(settings, "open_model", "meta-models/not-a-real-model")
    with pytest.raises(meta_client.MetaAPIError):
        meta_client.chat_json([{"role": "user", "content": "hi"}], {"type": "object"}, "ping", open_weights=True)


def test_health_reports_the_open_model(spark_open):
    h = TestClient(app).get("/api/health").json()
    assert h["open_weights"] is True and h["models"]["lakon"] == "meta-models/muse-spark-open"
    assert "meta-models/muse-spark-open" in h["open_weights_models"]


def test_env_var_switches_it_on_in_a_fresh_process(tmp_path):
    code = ("from api.config import settings; "
            "print(settings.open_weights_active, settings.open_model, settings.open_api_base)")
    env = {"PATH": "/usr/bin:/bin", "DATA_DIR": str(tmp_path), "FAKE_META": "1", "USE_OPEN_WEIGHTS": "true"}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["True", "meta-models/muse-spark-open", "https://inference.baseten.co/v1"]
    env["USE_OPEN_WEIGHTS"] = "false"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split()[0] == "False"


# ---------------------------------------------------------------- per-stage open-weights routing
def test_open_weights_stages_route_text_stages_to_baseten(monkeypatch):
    from api import cost, fake_meta, meta_client
    from api.config import settings
    from api.jobs import Job
    from api.pipeline import director, mock
    from api.schemas import Script

    monkeypatch.setattr(settings, "use_open_weights", True)
    monkeypatch.setattr(settings, "open_stages", frozenset({"director", "lakon"}))
    assert meta_client.routes_open("director") and meta_client.routes_open("lakon")
    assert not meta_client.routes_open("verdict") and not meta_client.routes_open("motion_plan")
    m = cost.Meter(5.0)
    cost.use(m)
    try:
        job = Job.create("id", "classic", True)
        script = Script(**mock.SAMPLE_SCRIPT)
        out = director.plan(job, script)
    finally:
        cost.use(None)
    assert out["source"] == settings.open_model
    call = next(e for e in m.trace if e.get("kind") == "call")
    assert call["model"].startswith("meta-models/muse-spark-open")
    assert m.spent == 0  # billed by the host, not by Meta
    assert fake_meta.CALLS[-1].endswith("/chat/completions")
    monkeypatch.setattr(settings, "open_stages", frozenset({"lakon"}))
    assert not meta_client.routes_open("director")
