"""Go-live safety net: jittered back-off, circuit breaker, spend caps, record/replay, per-stage fallback."""
import json
import os

import httpx
import pytest

from api import cost, fake_meta, meta_client, resilience, runner
from api.config import settings
from api.jobs import Job
from api.pipeline import mock


@pytest.fixture
def meter():
    m = cost.Meter(5.0)
    cost.use(m)
    yield m
    cost.use(None)


@pytest.fixture
def no_sleep(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(meta_client.time, "sleep", waits.append)
    return waits


def test_backoff_has_jitter_and_honours_retry_after():
    waits = {resilience.backoff(0) for _ in range(40)}
    assert all(2 <= w <= 2.5 for w in waits) and len(waits) > 1
    assert 8 <= resilience.backoff(2) <= 10
    assert resilience.backoff(0, "12") == 12
    assert resilience.backoff(0, "999") == 30  # capped
    assert 2 <= resilience.backoff(0, "soon") <= 2.5


def test_breaker_opens_after_repeated_failures_and_recovers(monkeypatch):
    b = resilience.Breaker(threshold=2, cooldown=10)
    assert b.state == "closed" and b.allow()
    b.failure()
    assert b.state == "closed"
    b.failure()
    assert b.state == "open" and not b.allow()
    b.opened_at -= 11  # cooldown passed
    assert b.state == "half_open" and b.allow()
    b.failure()  # the trial call failed: open again
    assert b.state == "open"
    b.opened_at -= 11
    b.success()
    assert b.state == "closed"


def test_open_breaker_short_circuits_calls(monkeypatch, no_sleep, meter):
    monkeypatch.setenv("BREAKER_THRESHOLD", "2")
    resilience.reset_breakers()
    n = []

    def down(req):
        n.append(1)
        return httpx.Response(503, text="down")

    monkeypatch.setattr(meta_client, "_clients", {settings.fake_meta: httpx.Client(transport=httpx.MockTransport(down))})
    for _ in range(2):
        with pytest.raises(meta_client.MetaAPIError):
            meta_client._post("https://api.meta.ai/v1/x", json={"model": "muse-image-1.0"}, retries=1)
    calls = len(n)
    with pytest.raises(meta_client.MetaAPIError, match="circuit open"):
        meta_client._post("https://api.meta.ai/v1/x", json={"model": "muse-image-1.0"}, retries=1)
    assert len(n) == calls  # no request went out
    assert resilience.breaker_states()["muse-image-1.0"] == "open"
    assert any(e.get("error") == "circuit open" for e in meter.trace)


def test_client_errors_do_not_open_the_breaker(monkeypatch, no_sleep, meter):
    monkeypatch.setenv("BREAKER_THRESHOLD", "1")
    resilience.reset_breakers()
    monkeypatch.setattr(meta_client, "_clients", {settings.fake_meta: httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(400, json={"error": {"message": "content_policy"}})))})
    for _ in range(3):
        with pytest.raises(meta_client.MetaAPIError, match="400"):
            meta_client._post("https://api.meta.ai/v1/x", json={"model": "m"})
    assert resilience.breaker("m").state == "closed"


def test_total_spend_cap_blocks_real_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "meta_api_key", "real")
    monkeypatch.setattr(settings, "fake_flag", False)
    monkeypatch.setenv("MAX_USD_TOTAL", "0.02")
    cost.charge("muse-image-1.0", 0.01)
    assert resilience.ledger.total() == pytest.approx(0.01)
    cost.check(0.01)  # exactly at the cap is fine
    cost.charge("muse-image-1.0", 0.01)
    with pytest.raises(cost.BudgetExceeded, match="MAX_USD_TOTAL"):
        cost.check(0.01)
    monkeypatch.setenv("MAX_USD_TOTAL", "0")  # 0 = no cap
    cost.check(5.0)


def test_fake_spend_never_counts_toward_the_total(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    cost.charge("muse-image-1.0", 0.5)
    assert resilience.ledger.total() == 0.0


def test_max_usd_per_film_alias(monkeypatch):
    from api.config import Settings

    monkeypatch.setenv("MAX_USD_PER_FILM", "0.75")
    assert Settings().job_budget_usd == 0.75


def test_record_then_replay_without_network(monkeypatch, tmp_path, meter):
    rec = tmp_path / "fx"
    monkeypatch.setattr(settings, "meta_record_dir", str(rec))
    monkeypatch.setattr(meta_client, "_clients", {})
    out = meta_client.chat_json([{"role": "user", "content": "STORY (code 'en')"}], {}, "lakon")
    meta_client.generate_image("a wayang backdrop", tmp_path / "a.png")
    files = list(rec.glob("*.json"))
    assert len(files) == 2
    saved = json.loads(files[0].read_text())
    assert "authorization" not in json.dumps(saved).lower()  # keys are never written
    monkeypatch.setattr(settings, "meta_record_dir", "")
    monkeypatch.setattr(settings, "meta_replay_dir", str(rec))
    monkeypatch.setattr(meta_client, "_clients", {})
    before = len(fake_meta.CALLS)
    assert meta_client.chat_json([{"role": "user", "content": "STORY (code 'en')"}], {}, "lakon") == out
    # a slightly different prompt still gets the loose match (same endpoint, model and schema)
    assert meta_client.chat_json([{"role": "user", "content": "another story"}], {}, "lakon")["scenes"]
    meta_client.generate_image("a wayang backdrop", tmp_path / "b.png")
    assert (tmp_path / "b.png").read_bytes() == (tmp_path / "a.png").read_bytes()
    assert len(fake_meta.CALLS) == before  # nothing reached the (fake) network
    with pytest.raises(meta_client.MetaAPIError, match="no recorded fixture"):
        meta_client.chat_json([{"role": "user", "content": "x"}], {}, "motion_plan")
    monkeypatch.setattr(meta_client, "_clients", {})


def test_redaction_hashes_media():
    big = "data:image/png;base64," + "A" * 5000
    red = resilience._redact({"images": [{"image_url": big}], "prompt": "short"})
    assert red["images"][0]["image_url"].startswith("sha256:") and red["prompt"] == "short"


def test_fake_failure_injection_once_and_always(meter, no_sleep):
    os.environ["FAKE_META_FAIL"] = "images:once"
    with pytest.raises(meta_client.MetaAPIError):
        meta_client._post("https://api.meta.ai/v1/images/generations", json={"model": "muse-image-1.0"}, retries=0,
                          headers=meta_client._headers())
    r = meta_client._post("https://api.meta.ai/v1/images/generations", headers=meta_client._headers(),
                          json={"model": "muse-image-1.0", "prompt": "x", "n": 1}, retries=0)
    assert r.status_code == 200
    os.environ["FAKE_META_FAIL"] = "motion_plan:always"
    for _ in range(2):
        with pytest.raises(meta_client.MetaAPIError, match="503"):
            meta_client.chat_json([{"role": "user", "content": "x"}], {}, "motion_plan")


def test_muse_image_outage_gives_a_labelled_placeholder_film_not_a_crash(no_sleep):
    import shutil

    shutil.rmtree(settings.data_dir / "cache", ignore_errors=True)  # no cached art from earlier tests
    os.environ["FAKE_META_FAIL"] = "images:always"
    job = Job.create("id", "classic", False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " outage")
    assert job.s["status"] == "done", job.s.get("error")
    assert all(c["placeholder"] for c in job.s["scenes"])
    assert all(c["placeholder"] for c in job.s["cast"])
    fb = job.s["fallbacks"]
    assert any(f["stage"] == "scenes" and f["placeholder"] for f in fb)
    assert any(f["label"] == "gunungan" for f in fb)
    assert any(e.get("agent") == "fallback" for e in job.s["trace"])
    assert (job.dir / "dalang_landscape.mp4").exists()


def test_checker_outage_keeps_pictures_unchecked(no_sleep):
    os.environ["FAKE_META_FAIL"] = "verdict:always"
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " checker down")
    assert job.s["status"] == "review", job.s.get("error")
    assert not any(c["placeholder"] for c in job.s["scenes"])
    assert any("checker unavailable" in f["what"] for f in job.s["fallbacks"])


def test_a_stage_with_no_fallback_stops_with_a_kind_message(no_sleep):
    os.environ["FAKE_META_FAIL"] = "lakon:always"
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " lakon down")
    assert job.s["status"] == "failed" and job.s["message"] == runner.UNREACHABLE


def test_trace_is_live_on_the_job_while_the_film_is_made(monkeypatch):
    seen: list[int] = []
    orig = Job.stage

    def spy(self, key, *a, **k):
        seen.append(len(self.s.get("trace") or []))
        return orig(self, key, *a, **k)

    monkeypatch.setattr(Job, "stage", spy)
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " live trace")
    assert job.s["status"] == "review"
    assert max(seen) > 0 and seen[-1] >= max(seen[:-1])  # entries appeared during the run, not only at the end
