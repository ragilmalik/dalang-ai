"""Runner failure paths: a stage that crashes, a blocked story, DEMO_MODE replay, privacy cleanup on failure."""
from __future__ import annotations

import pytest

from api import errors, runner
from api.config import settings
from api.jobs import Job
from api.pipeline import listen


def _job(**kw) -> Job:
    return Job.create("id", "classic", False, **kw)


def _run_stage(job: Job, fn) -> None:
    """Run `fn(job)` through the same guard the pipeline uses."""
    runner._guarded(fn)(job)


def test_crashing_stage_fails_the_film_and_marks_the_running_stage():
    job = _job()

    def boom(j: Job) -> None:
        j.stage("lakon", "running")
        raise RuntimeError("model said no")

    _run_stage(job, boom)
    assert job.s["status"] == "failed"
    # the family sees a kind bilingual message, never the raw exception text (that goes to the server log)
    assert job.s["error"] == errors.MESSAGES["internal"] and job.s["error_kind"] == "internal"
    assert "model said no" not in job.s["error"]
    lakon = next(s for s in job.s["stages"] if s["key"] == "lakon")
    assert lakon["status"] == "failed"
    assert lakon["detail"] == errors.MESSAGES["internal"]


def test_long_error_is_trimmed():
    job = _job()

    def boom(j: Job) -> None:
        raise RuntimeError("x" * 2000)

    _run_stage(job, boom)
    assert len(job.s["error"]) <= 500


def test_blocked_story_is_blocked_not_failed():
    job = _job()

    def nope(j: Job) -> None:
        raise listen.Blocked("Cerita ini tidak cocok untuk anak-anak.")

    _run_stage(job, nope)
    assert job.s["status"] == "blocked"
    assert "anak-anak" in job.s["message"]
    assert not job.s.get("error")


def test_failure_always_deletes_the_childs_recording():
    job = _job()
    rec = job.dir / "story.wav"
    rec.write_bytes(b"RIFF")
    job.set(voice_turns=[{"start": 0.0, "end": 1.0, "text": "halo"}])

    def boom(j: Job) -> None:
        raise ValueError("render broke")

    _run_stage(job, boom)
    assert not rec.exists()
    assert all("text" not in t for t in job.s["voice_turns"])


def test_cost_is_recorded_even_when_the_stage_fails():
    job = _job()

    def boom(j: Job) -> None:
        from api import cost

        cost.charge("muse-image", 0.07)
        raise RuntimeError("late failure")

    _run_stage(job, boom)
    assert job.s["cost_usd"] == pytest.approx(0.07)
    assert job.s["cost_items"]["muse-image"] == pytest.approx(0.07)


def test_success_leaves_a_running_job_untouched_and_keeps_recording():
    job = _job()
    rec = job.dir / "story.wav"
    rec.write_bytes(b"RIFF")

    def ok(j: Job) -> None:
        j.set(status="review")

    _run_stage(job, ok)
    assert job.s["status"] == "review"
    assert rec.exists()  # a storyboard in review keeps it until the film is made (or the sweep removes it)


def test_demo_mode_replays_the_prepared_film_on_failure(monkeypatch, tmp_path):
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "dalang_landscape.mp4").write_bytes(b"landscape")
    (demo / "dalang_vertical.mp4").write_bytes(b"vertical")
    (demo / "poster.jpg").write_bytes(b"jpg")
    (demo / "job.json").write_text('{"title": "Kancil dan Buaya", "script": null}')
    monkeypatch.setattr(runner, "DEMO_DIR", demo)
    monkeypatch.setattr(settings, "demo_mode", True)
    job = _job()

    def boom(j: Job) -> None:
        j.stage("scenes", "running")
        raise RuntimeError("Meta API timeout")

    _run_stage(job, boom)
    assert job.s["status"] == "done"
    assert job.s["demo_replay"] is True
    assert job.s["title"] == "Kancil dan Buaya"
    assert set(job.s["videos"]) == {"landscape", "vertical"}
    assert (job.dir / "dalang_landscape.mp4").read_bytes() == b"landscape"
    assert "film made earlier" in job.s["message"] and "Meta API timeout" not in job.s["message"]
    assert not job.s.get("error")


def test_demo_mode_without_a_prepared_film_still_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "DEMO_DIR", tmp_path / "missing")
    monkeypatch.setattr(settings, "demo_mode", True)
    job = _job()

    def boom(j: Job) -> None:
        raise RuntimeError("no film to fall back on")

    _run_stage(job, boom)
    assert job.s["status"] == "failed"
    assert not job.s.get("demo_replay")


def test_demo_mode_off_never_replays(monkeypatch, tmp_path):
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "dalang_landscape.mp4").write_bytes(b"x")
    monkeypatch.setattr(runner, "DEMO_DIR", demo)
    monkeypatch.setattr(settings, "demo_mode", False)
    assert runner.replay_demo(_job(), "anything") is False


def test_meter_is_cleared_after_every_run():
    from api import cost

    def boom(j: Job) -> None:
        raise RuntimeError("x")

    _run_stage(_job(), boom)
    assert cost.current() is None
