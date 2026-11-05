"""Job cache and wake-ups, plus the QR helpers."""
import threading
import time

from PIL import Image

from api import db, qr
from api.jobs import Job


def test_get_loads_from_the_database_when_not_cached():
    job = Job.create("id", "classic", True)
    Job.forget(job.id)
    again = Job.get(job.id)
    assert again is not None and again is not job and again.s["id"] == job.id
    assert Job.get(job.id) is again  # now cached


def test_get_unknown_job_is_none():
    assert Job.get("does-not-exist") is None


def test_forget_drops_only_the_cache_not_the_row():
    job = Job.create("en", "classic", False)
    Job.forget(job.id)
    Job.forget(job.id)  # forgetting twice is harmless
    assert db.load(job.id) is not None


def test_used_records_each_model_once():
    job = Job.create("id", "classic", True)
    job.used("muse-spark-1.2")
    job.used("muse-spark-1.2")
    assert job.s["models"].count("muse-spark-1.2") == 1


def test_wait_change_returns_at_once_when_already_newer():
    job = Job.create("id", "classic", True)
    seen = job.version
    job.set(detail="x")
    t = time.time()
    assert job.wait_change(seen, timeout=5) > seen
    assert time.time() - t < 1


def test_wait_change_times_out_without_news():
    job = Job.create("id", "classic", True)
    seen = job.version
    t = time.time()
    assert job.wait_change(seen, timeout=0.2) == seen
    assert 0.15 < time.time() - t < 2


def test_wait_change_wakes_when_another_thread_saves():
    job = Job.create("id", "classic", True)
    seen = job.version
    threading.Timer(0.1, lambda: job.set(detail="woke")).start()
    t = time.time()
    assert job.wait_change(seen, timeout=5) > seen
    assert time.time() - t < 3


def test_qr_png_bytes_and_save(tmp_path):
    data = qr.png_bytes("https://example.com/watch/abc")
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    out = qr.save("https://example.com/watch/abc", tmp_path / "deep" / "q.png", box=4)
    assert out.exists()
    with Image.open(out) as im:
        assert im.mode == "RGB" and im.width == im.height
