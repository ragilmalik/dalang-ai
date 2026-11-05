"""Cost meter, agent trace summary and storage publish: pure unit tests, no network."""
from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import cost, storage


@pytest.fixture(autouse=True)
def _no_meter():
    cost.use(None)
    yield
    cost.use(None)


def test_charge_tokens_uses_price_table():
    m = cost.Meter(1.0)
    cost.use(m)
    cost.charge_tokens("muse-spark-1.3", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert m.spent == pytest.approx(1.25 + 4.25)
    cost.charge_tokens("muse-wonder-1.0", {"input_tokens": 500_000, "output_tokens": 0})
    assert m.items["muse-wonder-1.0"] == pytest.approx(2.0)


def test_charge_tokens_ignores_unknown_model_and_missing_usage():
    m = cost.Meter(1.0)
    cost.use(m)
    cost.charge_tokens("mystery-model", {"prompt_tokens": 10**6})
    cost.charge_tokens("muse-spark-1.3", None)
    assert m.spent == 0.0


def test_no_meter_is_a_noop():
    cost.charge("x", 5.0)
    cost.check(99.0)
    cost.record_call("m", "e", "p", 1.0, 1, True)
    cost.record_decision("nothing")
    assert cost.current() is None


def test_budget_check_raises_only_when_exceeded():
    m = cost.Meter(0.10)
    cost.use(m)
    m.charge("muse-image", 0.05)
    cost.check(0.05)  # exactly at budget is allowed
    with pytest.raises(cost.BudgetExceeded) as exc:
        cost.check(0.06)
    assert "$0.10" in str(exc.value)


def test_trace_is_capped_to_newest_entries():
    m = cost.Meter(1.0)
    for i in range(cost.TRACE_MAX + 25):
        m.record({"kind": "decision", "agent": "verify", "text": str(i)})
    assert len(m.trace) == cost.TRACE_MAX
    assert m.trace[-1]["text"] == str(cost.TRACE_MAX + 24)
    assert m.trace[0]["text"] == "25"


def test_record_stamps_stage_and_time():
    m = cost.Meter(1.0)
    m.stage_of = lambda: "scenes"
    cost.use(m)
    cost.record_decision("redraw scene 2")
    entry = m.trace[0]
    assert entry["stage"] == "scenes" and entry["t"] > 0


def test_labelled_names_calls_and_restores():
    m = cost.Meter(1.0)
    cost.use(m)
    with cost.labelled("puppet Si Kancil"):
        cost.record_call("muse-image-1.0", "images", "draw", 12.4, 2, False, error="x" * 500)
        cost.record_decision("too dark")
        with cost.labelled("inner"):
            assert cost.label() == "inner"
        assert cost.label() == "puppet Si Kancil"
    assert cost.label() is None
    call, decision = m.trace
    assert call["purpose"].endswith("puppet Si Kancil") and call["ms"] == 12
    assert len(call["error"]) == 160 and call["ok"] is False
    assert decision["text"] == "puppet Si Kancil: too dark"


def test_labelled_restores_after_exception():
    with pytest.raises(ValueError), cost.labelled("boom"):
        raise ValueError
    assert cost.label() is None


def test_summary_totals_failures_retries_and_decisions():
    trace = [
        {"kind": "call", "model": "a", "ok": True, "attempts": 1, "ms": 100},
        {"kind": "call", "model": "a", "ok": False, "attempts": 3, "ms": 50},
        {"kind": "call", "model": "b", "ok": True, "attempts": 1, "ms": 10},
        {"kind": "decision", "agent": "verify", "text": "redraw"},
    ]
    s = cost.summary(trace, {"a": 0.123456, "c": 1.0})
    by = {r["model"]: r for r in s["models"]}
    assert s["calls"] == 3 and s["decisions"] == 1
    assert by["a"] == {"model": "a", "calls": 2, "failed": 1, "retries": 2, "ms": 150, "usd": 0.1235}
    assert by["c"]["calls"] == 0 and by["c"]["usd"] == 1.0
    assert s["models"][0]["model"] == "a"  # most calls first


def test_publish_local_returns_job_url(monkeypatch, tmp_path):
    monkeypatch.setattr(storage.settings, "storage_backend", "local", raising=False)
    job = SimpleNamespace(id="abc", url=lambda p: f"/media/abc/{Path(p).name}")
    assert storage.publish(job, tmp_path / "film.mp4") == "/media/abc/film.mp4"


def test_publish_r2_uploads_and_returns_public_url(monkeypatch, tmp_path):
    calls: dict = {}

    class FakeS3:
        def upload_file(self, filename, bucket, key, ExtraArgs=None):
            calls["upload"] = (filename, bucket, key, ExtraArgs)

    def client(name, **kw):
        calls["client"] = (name, kw)
        return FakeS3()

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=client))
    for k, v in {"storage_backend": "r2", "r2_bucket": "films", "r2_account_id": "acct", "r2_access_key": "k",
                 "r2_secret_key": "s", "r2_public_url": "https://cdn.example"}.items():
        monkeypatch.setattr(storage.settings, k, v, raising=False)
    job = SimpleNamespace(id="abc", url=lambda p: "local")
    out = storage.publish(job, tmp_path / "poster.jpg", "image/jpeg")
    assert out == "https://cdn.example/films/abc/poster.jpg"
    assert calls["upload"][1:] == ("films", "films/abc/poster.jpg", {"ContentType": "image/jpeg"})
    assert calls["client"][1]["endpoint_url"] == "https://acct.r2.cloudflarestorage.com"


def test_publish_r2_without_bucket_falls_back_to_local(monkeypatch, tmp_path):
    monkeypatch.setattr(storage.settings, "storage_backend", "r2", raising=False)
    monkeypatch.setattr(storage.settings, "r2_bucket", "", raising=False)
    job = SimpleNamespace(id="abc", url=lambda p: "local-url")
    assert storage.publish(job, tmp_path / "f.mp4") == "local-url"
