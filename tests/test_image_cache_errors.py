"""Regression for the Nov 3 screenshot bug: two films with the same story painted the same backdrop at once; one
copied the shared image-cache entry while the other was still writing it, got a picture of zero bytes, and the film
page showed "cannot identify image file '/workspace/.../bg_1.png'" under "Painting the scenes".

Covers: atomic picture writes, one painter per cache entry, damaged cache entries painted again, and that no server
path, exception class name or traceback ever reaches the job / trace JSON a family can see."""
from __future__ import annotations

import io
import json
import re
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, UnidentifiedImageError

from api import errors, fileio, meta_client, runner
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import engine, mock, verify

client = TestClient(app)


def _png(color=(120, 80, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 40), color).save(buf, format="PNG")
    return buf.getvalue()


def _key(prompt: str, size: str = "1536x1024") -> Path:
    import hashlib

    tag = "fake" if settings.fake_meta else settings.image_model
    return settings.data_dir / "cache" / "img" / (hashlib.sha256(f"{tag}|{size}|{prompt}".encode()).hexdigest()[:32] + ".png")


# ---------------------------------------------------------------- file helpers
def test_atomic_write_leaves_no_temp_files_and_image_ok(tmp_path):
    p = fileio.atomic_write_bytes(tmp_path / "a.png", _png())
    assert fileio.image_ok(p)
    assert [f.name for f in tmp_path.iterdir()] == ["a.png"]
    (tmp_path / "zeros.png").write_bytes(b"\0" * 41927)  # what the race produced
    (tmp_path / "half.png").write_bytes(_png()[:30])
    (tmp_path / "empty.png").write_bytes(b"")
    assert not any(fileio.image_ok(tmp_path / n) for n in ("zeros.png", "half.png", "empty.png", "missing.png"))


def test_atomic_copy_replaces_the_target(tmp_path):
    (tmp_path / "src.png").write_bytes(_png((1, 2, 3)))
    (tmp_path / "dst.png").write_bytes(b"old")
    fileio.atomic_copy(tmp_path / "src.png", tmp_path / "dst.png")
    assert (tmp_path / "dst.png").read_bytes() == (tmp_path / "src.png").read_bytes()


# ---------------------------------------------------------------- the race
def test_same_prompt_from_two_films_at_once_never_copies_a_half_written_picture(monkeypatch, tmp_path):
    """The old cache did exists() -> copy while another thread was mid-write. A slow, non-atomic painter must not
    leak a torn file to any reader, and the picture is painted once."""
    prompt = f"race backdrop {time.time()}"
    painted = []

    def slow_nonatomic(p, out, size="1536x1024", **kw):
        painted.append(p)
        data = _png()
        with open(out, "wb") as f:  # truncate + write in pieces, like a plain write_bytes on a slow disk
            f.write(b"\0" * len(data))
            f.flush()
            time.sleep(0.2)
            f.seek(0)
            f.write(data)
        return out

    monkeypatch.setattr(meta_client, "generate_image", slow_nonatomic)
    outs = [tmp_path / f"bg_{i}.png" for i in range(6)]
    errs: list[BaseException] = []

    def go(o):
        try:
            verify.cached_generate(prompt, o, "1536x1024")
        except BaseException as e:  # noqa: BLE001
            errs.append(e)

    threads = [threading.Thread(target=go, args=(o,)) for o in outs]
    threads[0].start()
    time.sleep(0.05)  # the first film is mid-write when the others find the cache entry (old code: 1 of 6 valid)
    for t in threads[1:]:
        t.start()
    for t in threads:
        t.join()
    assert not errs
    assert len(painted) == 1
    assert all(fileio.image_ok(o) for o in outs)
    assert len({o.read_bytes() for o in outs}) == 1


def test_damaged_cache_entry_is_painted_again(monkeypatch, tmp_path):
    prompt = f"damaged entry {time.time()}"
    key = _key(prompt)
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_bytes(b"\0" * 41927)
    calls = []

    def gen(p, out, size="1536x1024", **kw):
        calls.append(p)
        return fileio.atomic_write_bytes(out, _png())

    monkeypatch.setattr(meta_client, "generate_image", gen)
    out = verify.cached_generate(prompt, tmp_path / "bg_1.png", "1536x1024")
    assert calls == [prompt] and fileio.image_ok(out) and fileio.image_ok(key)
    verify.cached_generate(prompt, tmp_path / "bg_2.png", "1536x1024")  # now a healthy hit
    assert calls == [prompt]


def test_unreadable_picture_from_the_model_becomes_a_placeholder(monkeypatch):
    prompt = f"garbage picture {time.time()}"
    monkeypatch.setattr(meta_client, "generate_image",
                        lambda p, out, size="1536x1024", **kw: fileio.atomic_write_bytes(out, b"not a png"))
    job = Job.create("id", "classic", True)
    rec = verify.make_verified(job, "scenes", "scene 1", prompt, job.dir / "bg_1.png", must_show="empty backdrop")
    assert rec["placeholder"] is True and fileio.image_ok(job.dir / "bg_1.png")
    assert not _key(prompt).exists()  # nothing damaged stays in the cache


def test_generate_image_writes_atomically(monkeypatch, tmp_path):
    out = meta_client.generate_image("an empty kelir backdrop", tmp_path / "x.png", size="1536x1024")
    assert fileio.image_ok(out)
    assert [f.name for f in tmp_path.iterdir()] == ["x.png"]


# ---------------------------------------------------------------- what a family sees
LEAKS = [re.compile(r"/workspace|/tmp/|/home/|/usr/|/var/|site-packages|\.py\b"),
         re.compile(r"\b[A-Z]\w*(?:Error|Exception)\b"), re.compile(r"Traceback")]


def _assert_clean(blob: str) -> None:
    assert str(settings.data_dir) not in blob
    for rx in LEAKS:
        m = rx.search(blob)
        assert not m, f"leak {m.group(0)!r} in: ...{blob[max(0, m.start() - 80):m.end() + 80]}..."


@pytest.mark.parametrize("raise_", [
    lambda p: UnidentifiedImageError(f"cannot identify image file '{p}'"),
    lambda p: FileNotFoundError(2, "No such file or directory", str(p)),
    lambda p: ValueError(f"bad value in {p} (json.JSONDecodeError: Expecting value)"),
])
def test_job_and_trace_json_never_show_paths_or_exception_names(monkeypatch, raise_):
    def broken_cover(path, *a, **kw):
        raise raise_(path if isinstance(path, Path) else settings.data_dir / "x.png")

    monkeypatch.setattr(engine, "cover", broken_cover)
    job = Job.create("id", "classic", True)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + f" (leak {time.time()})")
    assert job.s["status"] == "failed"
    scenes = next(s for s in job.s["stages"] if s["key"] == "scenes")
    assert scenes["status"] == "failed" and scenes["detail"] in errors.MESSAGES.values()
    assert job.s["error"] in errors.MESSAGES.values() and " \u00b7 " in job.s["error"]  # id · en
    _assert_clean(json.dumps(job.s))
    r = client.get(f"/api/jobs/{job.id}")
    assert r.status_code == 200
    _assert_clean(r.text)


def test_picture_failure_gets_the_picture_kind():
    kind, msg = errors.public(UnidentifiedImageError("cannot identify image file '/workspace/x/bg_1.png'"))
    assert kind == "picture" and "/workspace" not in msg and "Please try again" in msg


@pytest.mark.parametrize("raw, gone", [
    ("cannot identify image file '/workspace/p/work/r6/data-perf/jobs/Q/bg_1.png'", "/workspace"),
    ("PIL.UnidentifiedImageError: boom", "UnidentifiedImageError"),
    ("Traceback (most recent call last):\n  File \"/srv/app.py\", line 1", "Traceback"),
    ("open C:\\Users\\x\\bg.png failed", "C:\\"),
])
def test_scrub_removes_paths_class_names_and_tracebacks(raw, gone):
    assert gone not in errors.scrub(raw)


@pytest.mark.parametrize("keep", ["1 of 5 scenes painted and checked", "Ki Dalang · id/en",
                                  "503 from https://api.meta.ai/v1/images/generations", "/media/abc/bg_1.png?v=1",
                                  "HTTP 401", "circuit open"])
def test_scrub_keeps_ordinary_details(keep):
    assert errors.scrub(keep) == keep


def test_fallback_and_decisions_are_scrubbed():
    from api import cost, resilience

    job = Job.create("id", "classic", True)
    meter = cost.Meter(1.0)
    cost.use(meter)
    try:
        resilience.fallback(job, "scenes", "scene 1", f"scene 1: redraw failed (OSError: {settings.data_dir}/x.png)")
        cost.record_call("muse-image", "/v1/images", "paint", 1.0, 1, False, f"read {settings.data_dir}/jobs/a.png")
    finally:
        cost.use(None)
    _assert_clean(json.dumps(job.s) + json.dumps(meter.trace))
