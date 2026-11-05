"""Sample gallery films: different stories and languages on the fake API, labelled sample, listed after real films."""
import time

from fastapi.testclient import TestClient

from api import fake_meta, samples
from api.config import settings
from api.main import app
from api.pipeline import mock
from api.schemas import Script

client = TestClient(app)


def test_fake_api_picks_the_script_that_matches_the_story():
    assert fake_meta.sample_script_for(mock.SAMPLE_TRANSCRIPT_TIMUN_JV)["title"] == "Timun Mas lan Buto Ijo"
    assert fake_meta.sample_script_for(mock.SAMPLE_TRANSCRIPT_SNAIL_EN)["title"] == "The Golden Snail"
    assert fake_meta.sample_script_for(mock.SAMPLE_TRANSCRIPT)["title"] == mock.SAMPLE_SCRIPT["title"]
    assert fake_meta.sample_script_for(mock.SAMPLE_TRANSCRIPT_JV)["title"] == mock.SAMPLE_SCRIPT["title"]  # Javanese Kancil


def test_sample_scripts_are_valid_and_in_their_own_language():
    for raw, lang in ((mock.SAMPLE_SCRIPT_TIMUN, "jv"), (mock.SAMPLE_SCRIPT_SNAIL, "en")):
        s = Script(**raw)
        assert s.language == lang and 4 <= len(s.scenes) <= 6 and all(c.cultural_note for c in s.characters)
    assert {x["language"] for x in samples.SAMPLES} == {"id", "jv", "en"}
    assert {x["style"] for x in samples.SAMPLES} == {"classic", "colorful"}


def test_seed_makes_a_labelled_public_sample_once_and_lists_it_after_family_films(monkeypatch):
    timun = next(x for x in samples.SAMPLES if x["key"] == "timun-mas-jv")
    monkeypatch.setattr(samples, "SAMPLES", [timun])
    made = samples.seed()
    assert len(made) == 1
    job = made[0]
    assert job.s["status"] == "done" and job.s["public"] and job.s["sample"] and job.s["language"] == "jv"
    assert job.s["title"].startswith("Timun Mas") and job.s["style"] == "colorful"
    assert samples.seed() == []  # already there: nothing redone

    # a family's own shared film comes before the sample in the gallery
    own = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "review": "false"}).json()["id"]
    for _ in range(600):
        if client.get(f"/api/jobs/{own}").json()["status"] in {"done", "failed"}:
            break
        time.sleep(0.2)
    client.post(f"/api/jobs/{own}/share", json={"public": True})
    g = client.get("/api/gallery").json()
    ids = [f["id"] for f in g]
    assert ids.index(own) < ids.index(job.id)
    item = next(f for f in g if f["id"] == job.id)
    assert item["sample"] is True and item["offline"] is True
    assert "Contoh" not in client.get(f"/api/jobs/{own}").text  # only samples carry the label


def test_startup_seeding_only_on_the_fake_api(monkeypatch):
    calls = []
    monkeypatch.setattr(samples, "seed_in_background", lambda: calls.append(1))
    monkeypatch.setattr(settings, "seed_samples", True)
    with TestClient(app):
        pass
    assert calls == [1]
    monkeypatch.setattr(settings, "fake_flag", False)
    monkeypatch.setattr(settings, "meta_api_key", "a-real-looking-key")
    with TestClient(app):
        pass
    assert calls == [1]  # with a real key nothing is spent on samples at startup
