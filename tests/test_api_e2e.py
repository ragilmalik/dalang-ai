"""Full pipeline through the HTTP API: create -> storyboard review -> edit/redo -> approve -> film -> share -> gallery."""
import json
import subprocess
import time

from fastapi.testclient import TestClient

from api import fake_meta
from api.main import app
from api.pipeline import media, mock

client = TestClient(app)


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.5)
    raise AssertionError(f"timeout, last status {j['status']}")


def test_health():
    h = client.get("/api/health").json()
    assert h["ok"] and h["fake_meta"] and h["models"]["animate"] == "muse-wonder-1.0"


def test_rejects_empty_request():
    assert client.post("/api/jobs", data={"language": "id"}).status_code == 400
    assert client.post("/api/jobs", data={"language": "xx", "text": "hi"}).status_code == 400


def test_moderation_blocks_war_story():
    j = client.post("/api/jobs", data={"text": "Cerita tentang perang dan bom di kota", "language": "id"}).json()
    j = wait(j["id"], {"blocked", "failed", "done", "review"})
    assert j["status"] == "blocked" and j["message"]


def test_full_flow_with_review(tmp_path):
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "language": "id", "style": "colorful",
                                       "review": "true"}).json()
    jid = j["id"]
    j = wait(jid, {"review", "failed", "blocked"})
    assert j["status"] == "review", j.get("error")
    assert [s["status"] for s in j["stages"][:4]] == ["done"] * 4
    assert len(j["scenes"]) == 5 and len(j["cast"]) == 2
    assert any(sc["rejections"] for sc in j["scenes"]), "verify agent should have redrawn one backdrop"
    assert client.get(j["scenes"][0]["still"]).status_code == 200

    # edit a line and repaint a scene during review
    old_still = j["scenes"][0]["still"]
    r = client.post(f"/api/jobs/{jid}/scenes/1", json={"narration": "Kancil yang cerdik lapar sekali.", "repaint": True})
    assert r.status_code == 200
    t0 = time.time()
    while time.time() - t0 < 120:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] == "review" and j["scenes"][0]["still"] != old_still:
            break
        time.sleep(0.3)
    assert j["scenes"][0]["narration"] == "Kancil yang cerdik lapar sekali."
    assert client.post(f"/api/jobs/{jid}/share", json={"public": True}).status_code == 409  # not finished yet

    assert client.post(f"/api/jobs/{jid}/approve").status_code == 200
    j = wait(jid, {"done", "failed"})
    assert j["status"] == "done", j.get("error")
    assert all(s["status"] in {"done", "skipped"} for s in j["stages"])
    assert set(j["models"]) >= {"muse-spark-1.3", "muse-image-1.0", "sam-3.1", "muse-wonder-1.0"}
    assert 0 < j["cost_usd"] < 1.5

    vid = client.get(j["videos"]["landscape"])
    assert vid.status_code == 200
    f = tmp_path / "film.mp4"
    f.write_bytes(vid.content)
    probe = subprocess.run([media.ffmpeg_exe(), "-i", str(f)], capture_output=True, text=True).stderr
    assert "Video: h264" in probe and "1280x720" in probe and "Audio: aac" in probe

    assert client.get("/api/gallery").json() == [] or all(g["id"] != jid for g in client.get("/api/gallery").json())
    assert client.post(f"/api/jobs/{jid}/share", json={"public": True}).json()["public"] is True
    assert any(g["id"] == jid for g in client.get("/api/gallery").json())


def test_sse_stream_sends_job_state():
    """Against a real uvicorn server (TestClient does not stream SSE incrementally)."""
    import socket
    import subprocess
    import sys

    import httpx

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--port", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        c = httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=120)
        deadline = time.time() + 90  # a busy machine (parallel test workers, CI) can take a while to import the app
        while True:
            try:
                c.get("/api/health")
                break
            except httpx.TransportError:
                assert srv.poll() is None, "uvicorn exited before it answered"
                assert time.time() < deadline, "uvicorn did not answer /api/health within 90 s"
                time.sleep(0.25)
        j = c.post("/api/jobs", data={"text": "Sebuah cerita kecil tentang Semar dan Gareng di sawah.",
                                      "language": "id", "review": "true"}).json()
        states = []
        with c.stream("GET", f"/api/jobs/{j['id']}/events") as r:  # the stream ends when the job reaches review
            assert r.headers["content-type"].startswith("text/event-stream")
            for line in r.iter_lines():
                if line.startswith("data: "):
                    states.append(json.loads(line[6:]))
        assert states[0]["id"] == j["id"] and states[-1]["status"] == "review" and len(states) > 3
    finally:
        srv.terminate()


def test_media_path_traversal_blocked():
    assert client.get("/media/abc/../../dalang.db").status_code == 404


def test_fake_logged_calls():
    assert any(p.endswith("/responses") for p in fake_meta.CALLS)
