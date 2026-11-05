"""Puppet box save errors over HTTP, the progress event stream, and loopback detection."""
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api import kotak, main
from api.jobs import Job

client = TestClient(main.app, raise_server_exceptions=False)
FAM = "fam_a1b2c3d4e5f6"


def carved_job(status: str = "done") -> Job:
    job = Job.create("id", "classic", True)
    (job.dir / "puppets").mkdir(exist_ok=True)
    Image.new("RGBA", (40, 60), (200, 100, 20, 255)).save(job.dir / "puppets" / "kancil.png")
    job.set(status=status, script={"characters": [{"id": "kancil", "name": "Kancil", "kind": "animal",
                                                  "wayang_archetype": "licik", "visual_description": "small deer"}]})
    return job


def test_keeping_an_unknown_puppet_is_404():
    job = carved_job()
    r = client.post("/api/kotak", json={"family_id": FAM, "job_id": job.id, "char_id": "nobody"})
    assert r.status_code == 404


def test_keeping_a_puppet_twice_returns_the_same_one():
    job = carved_job()
    body = {"family_id": FAM, "job_id": job.id, "char_id": "kancil"}
    a = client.post("/api/kotak", json=body)
    b = client.post("/api/kotak", json=body)
    assert a.status_code == 200 and b.status_code == 200 and a.json()["id"] == b.json()["id"]
    assert [p["id"] for p in client.get("/api/kotak", params={"family": FAM}).json()].count(a.json()["id"]) == 1


def test_a_full_box_is_409(monkeypatch):
    first = carved_job()
    fam = "fam_ffffffffffff"
    assert client.post("/api/kotak", json={"family_id": fam, "job_id": first.id, "char_id": "kancil"}).status_code == 200
    monkeypatch.setattr(kotak, "MAX_PUPPETS", 1)
    second = carved_job()
    r = client.post("/api/kotak", json={"family_id": fam, "job_id": second.id, "char_id": "kancil"})
    assert r.status_code == 409 and "holds" in r.text


def test_event_stream_for_a_finished_film_sends_one_state_and_ends():
    job = carved_job("done")
    with client.stream("GET", f"/api/jobs/{job.id}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        # no-transform: next start gzips responses (next.config.mjs compress: true) but must leave the stream alone
        assert "no-transform" in r.headers["cache-control"] and "content-encoding" not in r.headers
        lines = [ln for ln in r.iter_lines() if ln.startswith("data: ")]
    assert len(lines) == 1 and json.loads(lines[0][6:])["status"] == "done"


def test_event_stream_follows_a_running_film_until_it_finishes():
    job = carved_job("running")
    threading.Timer(0.8, lambda: job.set(status="done")).start()
    t = time.time()
    with client.stream("GET", f"/api/jobs/{job.id}/events") as r:
        states = [json.loads(ln[6:])["status"] for ln in r.iter_lines() if ln.startswith("data: ")]
    assert states[0] == "running" and states[-1] == "done" and time.time() - t < 10


def test_event_stream_for_unknown_film_is_404():
    assert client.get("/api/jobs/nope1234/events").status_code == 404


@pytest.mark.parametrize("ip,expected", [
    ("127.0.0.1", True), ("::1", True), ("::ffff:127.0.0.1", True), ("localhost", True),
    ("203.0.113.9", False), ("::ffff:203.0.113.9", False), ("not-an-ip", False),
])
def test_loopback_detection(ip, expected):
    assert main._loopback(ip) is expected
