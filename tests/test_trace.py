"""Agent trace ("Di balik kelir"): every Meta call and every agent decision of a film is recorded."""
import httpx
import pytest
from fastapi.testclient import TestClient

from api import cost, meta_client, runner
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import mock

client = TestClient(app)


def test_front_half_records_every_meta_call_and_the_verify_redraw():
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (trace)")
    assert job.s["status"] == "review"
    trace = job.s["trace"]
    calls = [e for e in trace if e["kind"] == "call"]
    models = {e["model"] for e in calls}
    assert {settings.lakon_model, settings.sam_model, settings.verify_model} <= models
    cache_hits = [e for e in trace if e["kind"] == "decision" and e.get("agent") == "cache"]
    assert settings.image_model in models or cache_hits  # Muse Image painted it, or the prompt-hash cache had it
    assert all(e["endpoint"].startswith("/v1/") and e["ms"] >= 0 and e["attempts"] >= 1 for e in calls)
    purposes = " | ".join(e["purpose"] for e in calls)
    assert "safety screen" in purposes and "write the lakon" in purposes and "cut out" in purposes
    assert "vision check against the script" in purposes and "scene 2" in purposes  # labelled per picture
    # the fake checker rejects scene 2 once: the agent decision is in the trace, in order, before the redraw passes
    decisions = [e["text"] for e in trace if e["kind"] == "decision"]
    assert any("scene 2" in d and "rejected attempt 1" in d for d in decisions)
    assert any("scene 2" in d and "redraw 1 passed" in d for d in decisions)
    assert all(e.get("stage") for e in calls)  # each call knows which stage it served
    summ = job.s["trace_summary"]
    assert summ["calls"] == len(calls) and summ["decisions"] == len(decisions)
    if settings.image_model in models:
        image_row = next(r for r in summ["models"] if r["model"] == settings.image_model)
        assert image_row["usd"] > 0


def test_back_half_appends_muse_wonder_plans_and_trace_endpoint():
    job = Job.create("en", "classic", False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (trace back)")
    assert job.s["status"] == "done"
    r = client.get(f"/api/jobs/{job.id}/trace").json()
    plans = [e for e in r["trace"] if e["kind"] == "call" and e["model"] == settings.animate_model]
    assert len(plans) == len(job.s["script"]["scenes"])
    assert all("choreograph" in e["purpose"] and "scene" in e["purpose"] for e in plans)
    assert r["summary"]["calls"] >= len(plans) and r["cost_usd"] == job.s["cost_usd"]
    client.post(f"/api/jobs/{job.id}/share", json={"public": True})
    entry = next(g for g in client.get("/api/gallery").json() if g["id"] == job.id)
    assert "trace" not in entry  # the public gallery never exposes the trace


def test_failed_call_is_recorded_with_its_attempts(monkeypatch):
    calls = {"n": 0}

    def boom(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="busy")

    monkeypatch.setattr(meta_client, "_clients", {settings.fake_meta: httpx.Client(transport=httpx.MockTransport(boom))})
    monkeypatch.setattr(meta_client.time, "sleep", lambda s: None)
    m = cost.Meter(1.0)
    cost.use(m)
    try:
        with pytest.raises(meta_client.MetaAPIError):
            meta_client.chat_json([{"role": "user", "content": "hi"}], {"type": "object"}, "lakon")
    finally:
        cost.use(None)
    assert calls["n"] == 4
    (entry,) = m.trace
    assert entry["ok"] is False and entry["attempts"] == 4 and entry["error"] == "HTTP 503"
    assert entry["model"] == settings.lakon_model and entry["endpoint"] == "/v1/chat/completions"


def test_trace_is_capped():
    m = cost.Meter(1.0)
    for i in range(cost.TRACE_MAX + 50):
        m.record({"kind": "decision", "text": str(i)})
    assert len(m.trace) == cost.TRACE_MAX and m.trace[-1]["text"] == str(cost.TRACE_MAX + 49)
