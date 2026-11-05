"""API corners: startup/shutdown logging, unknown style names, SSE keep-alive pings and disconnects,
oversized gara-gara answers."""
import asyncio
import itertools

from fastapi.testclient import TestClient

from api import main, runner
from api.jobs import Job
from api.main import app

client = TestClient(app)


def test_unknown_style_falls_back_to_classic(monkeypatch):
    started = []
    monkeypatch.setattr(runner, "start", lambda job, audio, text: started.append(job.id))  # no pipeline run needed
    r = client.post("/api/jobs", data={"text": "Kancil dan buaya menyeberang sungai bersama.", "language": "id",
                                       "style": "neon", "review": "true"})
    assert r.status_code == 200 and r.json()["style"] == "classic" and started == [r.json()["id"]]


def test_shutdown_logs_cancelled_films(monkeypatch, caplog):
    monkeypatch.setattr(runner, "shutdown", lambda: ["abc123", "def456"])
    with caplog.at_level("WARNING"), TestClient(app):
        pass
    assert any("2 queued film(s) cancelled" in m for m in caplog.messages)


def test_shutdown_is_quiet_when_nothing_was_queued(monkeypatch, caplog):
    monkeypatch.setattr(runner, "shutdown", lambda: [])
    with caplog.at_level("WARNING"), TestClient(app):
        pass
    assert not any("cancelled" in m for m in caplog.messages)


def test_oversized_gara_gara_answer_is_413(monkeypatch):
    job = Job.create("id", "classic", False, gara_gara=True)
    job.set(status="choice")
    monkeypatch.setattr(main, "MAX_UPLOAD", 10)
    r = client.post(f"/api/jobs/{job.id}/choice", files={"audio": ("a.webm", b"x" * 50, "audio/webm")})
    assert r.status_code == 413 and "25 MB" in r.json()["detail"]
    assert Job.get(job.id).s["status"] == "choice"  # still waiting, nothing started


def test_gara_gara_answer_with_empty_upload_and_no_text_is_400():
    job = Job.create("id", "classic", False, gara_gara=True)
    job.set(status="choice")
    r = client.post(f"/api/jobs/{job.id}/choice", files={"audio": ("a.webm", b"", "audio/webm")})
    assert r.status_code == 400


class FakeRequest:
    """Reports connected for the first `connected` checks, then disconnected."""

    def __init__(self, connected: int):
        self.left = connected

    async def is_disconnected(self) -> bool:
        if self.left <= 0:
            return True
        self.left -= 1
        return False


async def drain(jid: str, connected: int) -> list[str]:
    resp = await main.job_events(jid, FakeRequest(connected))
    return [chunk async for chunk in resp.body_iterator]


def test_sse_sends_a_keepalive_ping_while_a_film_is_quiet(monkeypatch):
    job = Job.create("id", "classic", False)
    job.set(status="running")
    clock = itertools.count(0, 20)  # every look at the clock is 20 s later
    monkeypatch.setattr(main.time, "time", lambda: next(clock))

    async def no_sleep(_):
        return None

    monkeypatch.setattr(main.asyncio, "sleep", no_sleep)
    chunks = asyncio.run(drain(job.id, connected=3))
    assert chunks[0].startswith("data: ") and '"running"' in chunks[0]
    assert ": ping\n\n" in chunks


def test_sse_stops_when_the_browser_disconnects(monkeypatch):
    job = Job.create("id", "classic", False)
    job.set(status="running")

    async def no_sleep(_):
        return None

    monkeypatch.setattr(main.asyncio, "sleep", no_sleep)
    chunks = asyncio.run(drain(job.id, connected=1))
    assert len(chunks) == 1  # the first state, then the loop sees the disconnect and ends


def test_sse_ends_on_a_waiting_state():
    job = Job.create("id", "classic", False)
    job.set(status="choice")
    chunks = asyncio.run(drain(job.id, connected=5))
    assert len(chunks) == 1 and '"choice"' in chunks[0]
