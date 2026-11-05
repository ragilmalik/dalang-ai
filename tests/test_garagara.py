"""Gara-gara interactive branching: pause after scene 2, the child answers, Muse Spark rewrites the rest,
only the new scenes are re-rendered, then the final cut."""
import math
import struct
import time
import wave

import pytest
from fastapi.testclient import TestClient

from api import meta_client
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import garagara, mock
from api.schemas import Script

client = TestClient(app)


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.3)
    raise AssertionError(f"timeout, last status {j['status']}")


def start(**form):
    data = {"text": mock.SAMPLE_TRANSCRIPT, "language": "id", "review": "false", "gara_gara": "true", **form}
    j = client.post("/api/jobs", data=data).json()
    return wait(j["id"], {"choice", "failed", "blocked", "done"})


def test_gara_gara_pauses_asks_and_rewrites_only_remaining_scenes():
    j = start()
    assert j["status"] == "choice", j.get("error")
    g = j["gara_gara"]
    assert g["after"] == 2 and g["status"] == "waiting" and len(g["options"]) == 2 and g["question"]
    assert g["speaker"] in {"kancil", "buaya"}
    assert [c["n"] for c in j["scenes"]] == [1, 2], "only the scenes before the pause are painted"
    assert client.get(j["part1"]).status_code == 200
    jdir = Job.get(j["id"]).dir
    m1 = (jdir / "motion_1.json").stat().st_mtime_ns
    before = j["script"]["scenes"][:2]

    r = client.post(f"/api/jobs/{j['id']}/choice", data={"text": g["options"][1]})
    assert r.status_code == 200
    j = wait(j["id"], {"done", "failed"})
    assert j["status"] == "done", j.get("error")
    assert j["gara_gara"]["answer"] == g["options"][1] and j["gara_gara"]["status"] == "answered"
    assert j["script"]["scenes"][:2] == before, "scenes before the gara-gara never change"
    assert g["options"][1].lower()[:10] in j["script"]["scenes"][2]["narration"].lower()
    assert j["fresh_scenes"] == [3, 4, 5]
    assert [c["n"] for c in j["scenes"]] == [1, 2, 3, 4, 5]
    assert (jdir / "motion_1.json").stat().st_mtime_ns == m1, "motion for kept scenes is reused, not re-planned"
    assert client.get(j["videos"]["landscape"]).status_code == 200


def test_choice_endpoint_guards():
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "language": "id", "review": "true"}).json()
    j = wait(j["id"], {"review", "failed"})
    assert client.post(f"/api/jobs/{j['id']}/choice", data={"text": "x"}).status_code == 409
    assert client.post("/api/jobs/nope/choice", data={"text": "x"}).status_code == 404
    j = start()
    assert client.post(f"/api/jobs/{j['id']}/choice", data={}).status_code == 400


def test_voice_answer_is_transcribed_and_deleted(tmp_path):
    j = start(review="true")
    assert j["status"] == "choice"
    wav = tmp_path / "a.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 7))) for i in range(16000)))
    with open(wav, "rb") as f:
        r = client.post(f"/api/jobs/{j['id']}/choice", files={"audio": ("answer.wav", f, "audio/wav")})
    assert r.status_code == 200
    j = wait(j["id"], {"review", "failed", "done"})
    assert j["status"] == "review", j.get("error")  # review comes after the choice
    assert "kancil" in j["gara_gara"]["answer"].lower()  # fake Muse Voice Transcribe transcript
    assert not list(Job.get(j["id"]).dir.glob("answer*")), "the voice answer is deleted after transcription"
    assert len(j["scenes"]) == 5


def test_unsafe_answer_asks_again():
    j = start()
    client.post(f"/api/jobs/{j['id']}/choice", data={"text": "pakai pistol dan bom"})
    j = wait(j["id"], {"choice", "failed", "done", "blocked"})
    assert j["status"] == "choice" and j["message"] and j["gara_gara"]["status"] == "waiting"


def test_rewrite_retries_once_then_validates(monkeypatch):
    job = Job.create("id", "classic", False)
    script = Script(**mock.SAMPLE_SCRIPT)
    good = {"moral": "m", "scenes": [dict(s) for s in mock.SAMPLE_SCRIPT["scenes"][2:]]}
    replies = iter([{"moral": "m", "scenes": [{"n": 3}]}, good])
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: next(replies))
    new = garagara.rewrite(job, script, 2, "q?", "a")
    assert len(new.scenes) == 5 and new.scenes[0].narration == script.scenes[0].narration


def test_rewrite_rejects_wrong_scene_count_twice(monkeypatch):
    job = Job.create("id", "classic", False)
    script = Script(**mock.SAMPLE_SCRIPT)
    one = {"moral": "m", "scenes": [dict(mock.SAMPLE_SCRIPT["scenes"][2])]}  # 2 kept + 1 = 3 scenes: too few
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: one)
    with pytest.raises(RuntimeError, match="invalid twice"):
        garagara.rewrite(job, script, 2, "q?", "a")


def test_split_point():
    s = Script(**mock.SAMPLE_SCRIPT)
    assert garagara.split_point(s) == 2
    six = dict(mock.SAMPLE_SCRIPT, scenes=mock.SAMPLE_SCRIPT["scenes"] + [mock.SAMPLE_SCRIPT["scenes"][0]])
    assert garagara.split_point(Script(**six)) == 3
    assert settings.fake_meta
