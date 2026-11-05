"""Restart safety: interrupted films are marked failed with a kind message, old private films are cleaned up,
queued work is cancelled on shutdown."""
from concurrent.futures import Future

from fastapi.testclient import TestClient

from api import db, runner
from api.config import settings
from api.jobs import Job
from api.main import app


def _orphan(status: str) -> Job:
    """A job left in `status` by a process that no longer exists."""
    job = Job.create("id", "classic", review=True)
    job.stage("lakon", "running")
    job.set(status=status)
    return job


def test_recover_marks_interrupted_jobs_failed_and_leaves_waiting_ones():
    stuck = [_orphan(s) for s in ("queued", "running", "rendering")]
    waiting = _orphan("review")
    recovered = runner.recover()
    for job in stuck:
        assert job.id in recovered
        s = Job.get(job.id).s
        assert s["status"] == "failed" and "try again" in s["message"].lower()
        assert next(st for st in s["stages"] if st["key"] == "lakon")["status"] == "failed"
        assert db.load(job.id)["status"] == "failed"  # persisted, so the browser sees it after a reload
    assert waiting.id not in recovered and Job.get(waiting.id).s["status"] == "review"


def test_recover_skips_jobs_this_process_is_running(monkeypatch):
    job = _orphan("running")
    pending: Future = Future()
    monkeypatch.setitem(runner._futures, job.id, pending)
    assert job.id not in runner.recover()
    assert job.s["status"] == "running"
    runner._futures.pop(job.id)


def test_startup_runs_recovery():
    job = _orphan("rendering")
    with TestClient(app) as c:
        assert c.get(f"/api/jobs/{job.id}").json()["status"] == "failed"


def test_shutdown_cancels_queued_work_and_tells_the_family(monkeypatch):
    job = _orphan("queued")
    pending: Future = Future()  # not started: cancel() succeeds
    monkeypatch.setitem(runner._futures, job.id, pending)
    assert runner.shutdown() == [job.id]
    assert pending.cancelled() and job.s["status"] == "failed" and "restart" in job.s["message"]
    runner._futures.pop(job.id)


def test_cleanup_removes_only_old_private_films():
    old_private, old_public, old_sample, fresh = (Job.create("id", "classic", review=True) for _ in range(4))
    old_public.set(public=True)
    old_sample.set(sample=True)
    for job in (old_private, old_public, old_sample):
        job.s["updated"] = 0
        (job.dir / "poster.jpg").write_bytes(b"x")
        with db._lock:
            conn = db._store.get()
            conn.execute("UPDATE jobs SET updated=0 WHERE id=?", (job.id,))
            conn.commit()
    assert runner.cleanup(0) == []  # off by default
    removed = runner.cleanup(30)
    assert old_private.id in removed
    assert not old_private.dir.exists() and db.load(old_private.id) is None and Job.get(old_private.id) is None
    for keep in (old_public, old_sample, fresh):
        assert keep.id not in removed and keep.dir.exists()
    assert settings.cleanup_days == 0


def _age(path, hours):
    import os
    import time

    t = time.time() - hours * 3600
    os.utime(path, (t, t))


def test_sweep_deletes_old_recordings_only(monkeypatch):
    old, fresh, busy, public_film = (Job.create("id", "classic", review=True) for _ in range(4))
    for job in (old, fresh, busy):
        (job.dir / "story.wav").write_bytes(b"RIFF")
    (old.dir / "upload.webm").write_bytes(b"x")
    (old.dir / "poster.jpg").write_bytes(b"x")
    old.set(voice_turns=[{"start_ms": 0, "end_ms": 900, "text": "private words"}])
    for f in (old.dir / "story.wav", old.dir / "upload.webm", busy.dir / "story.wav"):
        _age(f, 7)
    pending: Future = Future()
    monkeypatch.setitem(runner._futures, busy.id, pending)
    assert runner.sweep_recordings(0) == []  # off
    cleaned = runner.sweep_recordings(6)
    assert cleaned == [old.id]
    assert not (old.dir / "story.wav").exists() and not (old.dir / "upload.webm").exists()
    assert (old.dir / "poster.jpg").exists()  # only recordings go, never the film files
    assert "text" not in Job.get(old.id).s["voice_turns"][0]  # the words go with the audio
    assert (fresh.dir / "story.wav").exists() and (busy.dir / "story.wav").exists() and public_film.dir.exists()
    assert runner.sweep_recordings(6) == []  # idempotent
    runner._futures.pop(busy.id)


def test_new_film_triggers_the_sweep(monkeypatch):
    monkeypatch.setattr(runner, "start", lambda *a, **k: None)  # no pipeline needed to test the hook
    old = Job.create("id", "classic", review=True)
    (old.dir / "story.wav").write_bytes(b"RIFF")
    _age(old.dir / "story.wav", 30)
    with TestClient(app) as c:
        assert c.post("/api/jobs", data={"language": "en", "text": "A small goat climbs the mountain to find the moon.",
                                         "review": "true"}).status_code == 200
    assert not (old.dir / "story.wav").exists()
    assert settings.recording_ttl_hours == 6
