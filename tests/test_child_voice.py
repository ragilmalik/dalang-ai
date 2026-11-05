"""Child's own voice as narrator: scenes cut from the original recording using Muse Voice Transcribe's turn
timestamps; the recording is kept only until the film is made; TTS fallback without timestamps."""
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api import meta_client
from api.jobs import Job
from api.main import app
from api.pipeline import media, narrate

client = TestClient(app)
MP3 = Path(__file__).resolve().parents[1] / "assets" / "sample-story" / "sample_story_synthetic.mp3"


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.3)
    raise AssertionError(j["status"])


def turns(n, step=1000):
    return [{"start_ms": i * step, "end_ms": i * step + 800, "text": f"t{i}"} for i in range(n)]


def test_child_groups_cover_every_scene_in_order():
    g = narrate.child_groups(turns(7), 5)
    assert g is not None and len(g) == 5 and all(g)
    flat = [t["text"] for grp in g for t in grp]
    assert flat == [f"t{i}" for i in range(7)]
    assert narrate.child_groups(turns(5), 5) == [[t] for t in turns(5)]
    assert narrate.child_groups(turns(3), 5) is None  # too few turns: fall back to TTS
    assert narrate.child_groups([], 4) is None


def make(voice="child", language="id", review="false"):
    with open(MP3, "rb") as f:
        j = client.post("/api/jobs", data={"language": language, "review": review, "narration_voice": voice},
                        files={"audio": ("story.mp3", f, "audio/mpeg")}).json()
    return j["id"]


def test_child_voice_cuts_scenes_from_recording_then_deletes_it():
    jid = make()
    job_dir = Job.get(jid).dir
    j = wait(jid, {"done", "failed", "blocked"})
    assert j["status"] == "done", j.get("error")
    narr = next(s for s in j["stages"] if s["key"] == "narrate")
    assert "child's own voice" in narr["detail"]
    assert not (job_dir / "story.wav").exists(), "the recording is deleted once the film is made"
    assert not list(job_dir.glob("upload*"))
    assert all("text" not in t for t in j["voice_turns"]), "timestamps kept, words dropped from the turn log"
    assert len(j["child_lines"]) == 5
    secs = [media.wav_seconds(job_dir / "voice" / f"scene_{n}.wav") for n in range(1, 6)]
    assert all(0.5 < s < 15 for s in secs) and 15 < sum(secs) < 40  # the 30 s recording, shared out
    vtt = (job_dir / "captions.vtt").read_text(encoding="utf-8")
    assert j["child_lines"]["1"].split(".")[0] in vtt, "subtitles show the child's own words"


def test_recording_kept_during_review_only():
    jid = make(review="true")
    j = wait(jid, {"review", "failed"})
    assert j["status"] == "review"
    assert (Job.get(jid).dir / "story.wav").exists()
    client.post(f"/api/jobs/{jid}/approve")
    j = wait(jid, {"done", "failed"})
    assert j["status"] == "done" and not (Job.get(jid).dir / "story.wav").exists()


def test_falls_back_to_tts_without_timestamps(monkeypatch):
    real = meta_client.transcribe_turns
    monkeypatch.setattr(meta_client, "transcribe_turns", lambda *a, **k: (real(*a, **k)[0], []))
    jid = make()
    j = wait(jid, {"done", "failed"})
    assert j["status"] == "done", j.get("error")
    assert j.get("voice_note") and not j.get("child_lines")
    narr = next(s for s in j["stages"] if s["key"] == "narrate")
    assert "child's own voice" not in narr["detail"]


def test_javanese_child_voice_falls_back():
    jid = make(language="jv")
    j = wait(jid, {"done", "failed"})
    assert j["status"] == "done" and j.get("voice_note") and not j.get("voice_turns")


def test_bad_narration_voice_rejected():
    r = client.post("/api/jobs", data={"text": "Sebuah cerita tentang kancil yang pintar.", "narration_voice": "robot"})
    assert r.status_code == 400
