"""Pipeline behaviour: safety, retries, the verify agent, budget, caching, DEMO_MODE, Javanese routing, privacy."""
import json
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api import fake_meta, meta_client, runner
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import lakon, mock, verify
from api.schemas import Script

client = TestClient(app)


def tone(path: Path, seconds: float = 2.0, sr: int = 22050) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 300 * i / sr)))
                               for i in range(int(sr * seconds))))
    return path


def make_job(review: bool = True, language: str = "id") -> Job:
    return Job.create(language, "classic", review)


# ---------------------------------------------------------------- safety screen
@pytest.mark.parametrize("story", [
    "Ceritanya tentang perang besar dan tentara yang menembak dengan pistol.",   # war / weapons
    "Ayo pilih partai ini di pemilu besok, jangan pilih yang lain.",              # politics
    "Kalau demam minum obat ini tiga kali sehari tanpa ke dokter.",              # medical advice
])
def test_moderation_blocks_with_friendly_message(story):
    job = make_job()
    runner._front(job, None, story)
    assert job.s["status"] == "blocked"
    assert job.s["message"] and len(job.s["message"]) < 200
    assert job.s["stages"][1]["status"] == "pending"  # never reached the script writer


# ---------------------------------------------------------------- lakon retry
def test_lakon_retries_once_after_invalid_json(monkeypatch):
    calls = []

    def flaky(messages, schema, name, **kw):
        calls.append(messages)
        if len(calls) == 1:
            return {"title": "broken"}  # fails pydantic validation
        return json.loads(json.dumps(mock.SAMPLE_SCRIPT))

    monkeypatch.setattr(meta_client, "chat_json", flaky)
    job = make_job()
    script = lakon.run(job, "Sebuah cerita unik tentang retry nomor satu.")
    assert len(calls) == 2 and "invalid" in calls[1][-1]["content"]
    assert script.title == mock.SAMPLE_SCRIPT["title"]


def test_lakon_fails_gracefully_after_second_invalid_json(monkeypatch):
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"title": "still broken"})
    job = make_job()
    with pytest.raises(RuntimeError, match="invalid twice"):
        lakon.run(job, "Sebuah cerita unik tentang retry nomor dua.")


def test_job_marked_failed_when_script_invalid(monkeypatch):
    real = meta_client.chat_json

    def fake(messages, schema, name, **kw):
        return {"title": "x"} if name == "lakon" else real(messages, schema, name, **kw)

    monkeypatch.setattr(meta_client, "chat_json", fake)
    job = make_job()
    runner._front(job, None, "Sebuah cerita unik tentang retry nomor tiga yang gagal.")
    assert job.s["status"] == "failed" and job.s["error_kind"] == "script"
    assert job.s["stages"][1]["status"] == "failed"


# ---------------------------------------------------------------- verify agent
def test_verify_agent_redraws_twice_then_keeps_and_flags(monkeypatch, tmp_path):
    from api.schemas import Verdict

    drawn = []

    def gen(prompt, out, size):
        drawn.append(prompt)
        return meta_client.generate_image(prompt, out, size=size)

    monkeypatch.setattr(verify, "check", lambda *a, **k: Verdict(passed=False, issues=["text in picture"],
                                                                   fix_prompt=f"fixed {len(drawn)}"))
    job = make_job()
    rec = verify.make_verified(job, "scenes", "scene 1", "original prompt", job.dir / "bg.png",
                               must_show="empty backdrop", generate=gen)
    assert len(drawn) == 1 + settings.max_verify_retries == 3
    assert drawn[0] == "original prompt" and drawn[1].startswith("fixed")
    assert rec["attempts"] == 3 and len(rec["rejections"]) == 3  # flagged for the storyboard
    assert (job.dir / "bg.png").exists()  # the last attempt is kept so the film still gets made


def test_verify_agent_accepts_after_one_redraw():
    job = make_job()
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (verify)")
    scenes = {s["n"]: s for s in job.s["scenes"]}
    assert len(scenes[2]["rejections"]) == 1 and scenes[2]["attempts"] == 2  # fake checker fails scene 2 once
    assert all(not s["rejections"] for n, s in scenes.items() if n != 2)


# ---------------------------------------------------------------- cost guard
def test_cost_guard_stops_job_over_budget(monkeypatch):
    monkeypatch.setattr(settings, "job_budget_usd", 0.004)  # less than one film's model calls
    job = make_job()
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (budget)")
    assert job.s["status"] == "failed" and "budget" in job.s["error"].lower()
    assert job.s["stages"][4]["status"] == "pending"  # stopped before animation
    assert job.s["cost_usd"] < 0.05


# ---------------------------------------------------------------- caches
def test_transcript_hash_cache_hit(monkeypatch):
    text = "Cerita cache: Semar menanam padi bersama Gareng dan Petruk di sawah."
    lakon.run(make_job(), text)
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: pytest.fail("cache miss: model called again"))
    assert lakon.run(make_job(), text).title == mock.SAMPLE_SCRIPT["title"]


# ---------------------------------------------------------------- DEMO_MODE
def test_demo_mode_replays_saved_film_when_meta_call_fails(monkeypatch, tmp_path):
    demo = settings.data_dir / "demo"
    demo.mkdir(parents=True, exist_ok=True)
    (demo / "dalang_landscape.mp4").write_bytes(b"\x00" * 2048)
    (demo / "poster.jpg").write_bytes(b"\xff\xd8\xff")
    (demo / "job.json").write_text(json.dumps({"title": "Film cadangan", "script": mock.SAMPLE_SCRIPT}))
    monkeypatch.setattr(settings, "demo_mode", True)

    def boom(*a, **k):
        raise meta_client.MetaAPIError("503 from https://api.meta.ai/v1/images/generations")

    monkeypatch.setattr(verify, "make_verified", boom)
    job = make_job(review=False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (demo)")
    assert job.s["status"] == "done" and job.s["demo_replay"] is True
    assert job.s["videos"]["landscape"] and "film made earlier" in job.s["message"]
    shutil.rmtree(demo)


def test_without_demo_mode_failure_is_reported(monkeypatch):
    monkeypatch.setattr(verify, "make_verified",
                        lambda *a, **k: (_ for _ in ()).throw(meta_client.MetaAPIError("500 boom")))
    job = make_job()
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (no demo)")
    assert job.s["status"] == "failed" and job.s["error_kind"] == "meta" and "500" not in job.s["error"]
    assert job.s["stages"][2]["status"] == "failed"


# ---------------------------------------------------------------- Javanese + privacy
def test_javanese_audio_routes_to_spark_audio_and_audio_is_deleted(tmp_path):
    job = make_job(language="jv")
    upload = tone(job.dir / "upload.wav")
    fake_meta.CALLS.clear()
    from api.pipeline import listen

    transcript = listen.run(job, upload, None)
    assert transcript == mock.SAMPLE_TRANSCRIPT_JV
    assert not any(p.endswith("/asr/transcribe") for p in fake_meta.CALLS)  # Voice Transcribe skipped
    assert any(p.endswith("/chat/completions") for p in fake_meta.CALLS)
    assert not upload.exists() and not (job.dir / "story.wav").exists()


def test_indonesian_audio_uses_voice_transcribe_and_is_deleted(tmp_path):
    job = make_job(language="id")
    upload = tone(job.dir / "upload.wav")
    fake_meta.CALLS.clear()
    from api.pipeline import listen

    listen.run(job, upload, None)
    assert any(p.endswith("/asr/transcribe") for p in fake_meta.CALLS)
    assert not upload.exists() and not (job.dir / "story.wav").exists()
    assert not list(job.dir.glob("*.wav")) and not list(job.dir.glob("upload*"))


# ---------------------------------------------------------------- limits and sharing
def test_more_than_six_scenes_rejected():
    raw = json.loads(json.dumps(mock.SAMPLE_SCRIPT))
    raw["scenes"] = raw["scenes"] + raw["scenes"][:2]  # 7 scenes
    with pytest.raises(ValidationError):
        Script(**raw)


def test_more_than_four_characters_rejected():
    raw = json.loads(json.dumps(mock.SAMPLE_SCRIPT))
    raw["characters"] = raw["characters"] * 3
    with pytest.raises(ValidationError):
        Script(**raw)


def test_unshared_films_stay_out_of_gallery():
    job = make_job(review=False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (share)")
    assert job.s["status"] == "done"
    ids = lambda: {g["id"] for g in client.get("/api/gallery").json()}  # noqa: E731
    assert job.id not in ids()
    client.post(f"/api/jobs/{job.id}/share", json={"public": True})
    assert job.id in ids()
    client.post(f"/api/jobs/{job.id}/share", json={"public": False})
    assert job.id not in ids()
    # gallery entries expose only public fields (no transcript)
    client.post(f"/api/jobs/{job.id}/share", json={"public": True})
    entry = next(g for g in client.get("/api/gallery").json() if g["id"] == job.id)
    assert "transcript" not in entry


def test_applause_only_for_public_films_and_gallery_shows_count():
    job = make_job(review=False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (applause)")
    assert client.post(f"/api/jobs/{job.id}/applause").status_code == 404  # private film
    client.post(f"/api/jobs/{job.id}/share", json={"public": True})
    for n, ip in ((1, "203.0.113.21"), (2, "203.0.113.22")):  # two visitors
        assert client.post(f"/api/jobs/{job.id}/applause", headers={"x-forwarded-for": ip}).json()["applause"] == n
    entry = next(g for g in client.get("/api/gallery").json() if g["id"] == job.id)
    assert entry["applause"] == 2


def test_film_has_captions_opening_and_cultural_notes():
    job = make_job(review=False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (captions)")
    assert job.s["status"] == "done"
    vtt = (job.dir / "captions.vtt").read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT") and vtt.count("-->") == len(job.s["script"]["scenes"]) + (1 if (job.dir / "voice" / "opening.wav").exists() else 0)
    assert job.s["captions"].startswith(f"/media/{job.id}/captions.vtt")
    assert job.s["script"]["opening"].startswith("Kocap kacarita")
    assert all(c["cultural_note"] for c in job.s["script"]["characters"])
    timed = [s for s in job.s["stages"] if s["status"] == "done"]
    assert all("seconds" in s for s in timed)


def test_scenes_painted_in_parallel_keep_order():
    job = make_job()
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (parallel)")
    assert [c["n"] for c in job.s["scenes"]] == [1, 2, 3, 4, 5]
    assert job.s["cost_usd"] > 0  # worker threads charged the job's meter


def test_final_cut_renders_both_formats_in_parallel(monkeypatch):
    """16:9 and 9:16 render on two threads; both files exist, progress only rises, and an error surfaces."""
    import threading

    from api.pipeline import cut, engine

    seen_threads: set[str] = set()
    real_encode = engine.encode

    def spy(kel, out, fps, progress=None, poster=None):
        seen_threads.add(threading.current_thread().name)
        return real_encode(kel, out, fps, progress, poster)

    monkeypatch.setattr(engine, "encode", spy)
    monkeypatch.setattr(settings, "fps", 6)
    monkeypatch.setattr(settings, "make_vertical", True)
    details: list[str] = []
    real_stage = Job.stage

    def track(self, key, status=None, detail=None, **kw):
        if key == "cut" and detail and "%" in detail:
            details.append(detail)
        return real_stage(self, key, status, detail, **kw)

    monkeypatch.setattr(Job, "stage", track)
    job = make_job(review=False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " (parallel cut)")
    assert job.s["status"] == "done"
    assert (job.dir / "dalang_landscape.mp4").stat().st_size > 10_000
    assert (job.dir / "dalang_vertical.mp4").stat().st_size > 10_000
    assert len({t for t in seen_threads if t.startswith("ThreadPoolExecutor")}) == 2
    pcts = [int(d.split("...")[1].strip().rstrip("%")) for d in details]
    assert pcts == sorted(pcts) and len(set(pcts)) == len(pcts)

    def boom(*a, **k):
        raise RuntimeError("encoder exploded")

    monkeypatch.setattr(engine, "encode", boom)
    with pytest.raises(RuntimeError, match="encoder exploded"):
        cut.run(job, Script.model_validate(job.s["script"]), [{}] * len(job.s["script"]["scenes"]), [None] * 9)


def test_fake_checker_accepts_cached_redraw(tmp_path):
    """The redraw from the checker's fix prompt passes even when it comes from the image cache (no new fake call)."""
    import base64
    import io

    from PIL import Image

    from api import fake_meta, meta_client

    img = fake_meta._draw_for_prompt(fake_meta.FIX_PROMPT).resize((1536, 1024))
    p = tmp_path / "fix.png"
    img.save(p)
    part = meta_client.image_part(p)
    fp = fake_meta._digest(Image.open(io.BytesIO(base64.b64decode(part["image_url"]["url"].split(",", 1)[1]))).convert("RGB"))
    assert fake_meta._matches_fix(fp)
    other = tmp_path / "o.png"
    fake_meta._draw_for_prompt("dark river with tall reeds, tense").resize((1536, 1024)).save(other)
    part2 = meta_client.image_part(other)
    fp2 = fake_meta._digest(Image.open(io.BytesIO(base64.b64decode(part2["image_url"]["url"].split(",", 1)[1]))).convert("RGB"))
    assert not fake_meta._matches_fix(fp2)
