"""Abuse limits for a public deployment: upload size, story length, audio length, unreadable audio,
films in progress, and new films per visitor per hour."""
import io

import pytest
from fastapi.testclient import TestClient

from api import main
from api.config import settings
from api.jobs import Job
from api.pipeline import listen, media

client = TestClient(main.app)
STORY = "Kancil yang cerdik ingin menyeberang sungai, lalu ia menipu buaya dengan pintar sekali."


def _dirs() -> set[str]:
    return {p.name for p in (settings.data_dir / "jobs").glob("*")} if (settings.data_dir / "jobs").exists() else set()


def test_too_large_upload_is_refused_before_a_job_exists(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD", 1000)
    before, live = _dirs(), set(Job._live)
    r = client.post("/api/jobs", data={"language": "id"}, files={"audio": ("s.webm", io.BytesIO(b"x" * 2000), "audio/webm")})
    assert r.status_code == 413 and "25 MB" in r.json()["detail"]
    assert _dirs() == before and set(Job._live) == live  # no orphan job folder


def test_story_text_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "max_story_chars", 50)
    r = client.post("/api/jobs", data={"text": STORY, "language": "id"})
    assert r.status_code == 413 and "50" in r.json()["detail"]


def test_hourly_limit_per_visitor(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_hour", 2)
    monkeypatch.setattr(main, "_recent", {})
    monkeypatch.setattr(main.runner, "start", lambda *a, **k: None)  # don't run the pipeline here
    hdr = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
    codes = [client.post("/api/jobs", data={"text": STORY}, headers=hdr).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    other = client.post("/api/jobs", data={"text": STORY}, headers={"x-forwarded-for": "198.51.100.2"})
    assert other.status_code == 200  # another family is not affected
    here = TestClient(main.app, client=("127.0.0.1", 50000))
    local = [here.post("/api/jobs", data={"text": STORY}, headers={"x-forwarded-for": "127.0.0.1"}).status_code
             for _ in range(3)]
    assert local == [200, 200, 200]  # the machine itself (scripts, local demo, the Next.js proxy) is never limited
    spoof = [client.post("/api/jobs", data={"text": STORY}, headers={"x-forwarded-for": "127.0.0.1"}).status_code
             for _ in range(3)]
    assert spoof == [200, 200, 429]  # a visitor who claims to be 127.0.0.1 is still limited
    assert main._loopback("::ffff:127.0.0.1") and main._loopback("::1") and not main._loopback("203.0.113.7")


def test_busy_server_returns_kind_429(monkeypatch):
    monkeypatch.setattr(settings, "max_active_jobs", 1)
    monkeypatch.setattr(main.runner, "start", lambda *a, **k: None)
    busy = Job.create("id", "classic", True)
    busy.set(status="running")
    try:
        r = client.post("/api/jobs", data={"text": STORY})
        assert r.status_code == 429 and "busy" in r.json()["detail"]
    finally:
        busy.set(status="failed")


def test_long_recordings_are_trimmed(tmp_path):
    src = tmp_path / "long.wav"
    media.write_wav(src, media.np.zeros(16000 * 5))
    out = media.to_wav(src, tmp_path / "out.wav", max_seconds=2)
    assert media.wav_seconds(out) == pytest.approx(2.0, abs=0.05)


def test_unreadable_audio_is_a_kind_message_not_a_crash(tmp_path):
    job = Job.create("id", "classic", True)
    bad = tmp_path / "story.webm"
    bad.write_bytes(b"this is not audio at all")
    with pytest.raises(listen.Blocked) as e:
        listen.run(job, bad, None)
    assert "mp3, m4a, wav or webm" in str(e.value)
    assert not bad.exists()


def test_media_route_cannot_escape_the_jobs_folder():
    """Security: an encoded ".." as the film id used to make the data folder the base and serve the database."""
    (settings.data_dir / "jobs").mkdir(parents=True, exist_ok=True)
    for url in ("/media/%2E%2E/dalang.db", "/media/%2e%2e/jobs", "/media/..%2F/dalang.db", "/api/jobs/%2E%2E"):
        assert client.get(url).status_code == 404, url
    job = Job.create("id", "classic", True)
    (job.dir / "x.vtt").write_text("ok")
    assert client.get(f"/media/{job.id}/x.vtt").text == "ok"
    assert client.get(f"/media/{job.id}/..%2F..%2Fdalang.db").status_code == 404
