"""Stage 1 (listen) edge cases: nothing to hear, broken files, too-short stories, typed text, the child's voice."""
import math
import struct
import wave
from pathlib import Path

import pytest

from api import fake_meta, meta_client
from api.jobs import Job
from api.pipeline import listen, mock


def tone(path: Path, seconds: float = 2.0, sr: int = 22050) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 300 * i / sr)))
                               for i in range(int(sr * seconds))))
    return path


def make_job(language: str = "id", **extra) -> Job:
    return Job.create(language, "classic", True, **extra)


def test_no_audio_and_no_text_is_a_kind_block():
    job = make_job()
    with pytest.raises(listen.Blocked) as e:
        listen.run(job, None, None)
    assert "Rekam" in str(e.value) and "Record" in str(e.value)


def test_blank_text_counts_as_nothing():
    with pytest.raises(listen.Blocked):
        listen.run(make_job(), None, "   \n ")


def test_typed_story_skips_transcription_and_keeps_the_words():
    job = make_job(language="en")
    fake_meta.CALLS.clear()
    out = listen.run(job, None, "  The mouse deer tricked the crocodiles and crossed the river.  ")
    assert out == "The mouse deer tricked the crocodiles and crossed the river."
    assert job.s["transcript"] == out
    assert not any(p.endswith("/asr/transcribe") for p in fake_meta.CALLS)
    assert job.s["stages"][0]["status"] == "done"


def test_unreadable_recording_is_blocked_and_deleted():
    job = make_job()
    bad = job.dir / "upload.webm"
    bad.write_bytes(b"this is not audio at all" * 20)
    with pytest.raises(listen.Blocked) as e:
        listen.run(job, bad, None)
    assert "mp3" in str(e.value)
    assert not bad.exists()


@pytest.mark.parametrize("lang,needle", [("id", "Ceritanya"), ("jv", "Critane"), ("en", "couldn't hear")])
def test_too_short_story_asks_again_in_the_childs_language(monkeypatch, lang, needle):
    job = make_job(language=lang)
    monkeypatch.setattr(meta_client, "transcribe_turns", lambda *a, **k: ("hai kancil", []))
    monkeypatch.setattr(meta_client, "transcribe_with_spark_audio", lambda *a, **k: "hai kancil")
    upload = tone(job.dir / "upload.wav")
    with pytest.raises(listen.Blocked) as e:
        listen.run(job, upload, None)
    assert needle in str(e.value)
    assert not upload.exists() and not (job.dir / "story.wav").exists()


def test_child_voice_keeps_the_wav_only_when_turns_exist(monkeypatch):
    job = make_job(narration_voice="child")
    turns = [{"turnId": 0, "startMs": 0, "endMs": 1500, "transcript": "Dahulu ada kancil"}]
    monkeypatch.setattr(meta_client, "transcribe_turns", lambda *a, **k: (mock.SAMPLE_TRANSCRIPT, turns))
    listen.run(job, tone(job.dir / "upload.wav"), None)
    assert job.s["voice_turns"] == turns
    assert (job.dir / "story.wav").exists()  # kept until the film is made, then runner.forget_recording deletes it

    job2 = make_job(narration_voice="child")
    monkeypatch.setattr(meta_client, "transcribe_turns", lambda *a, **k: (mock.SAMPLE_TRANSCRIPT, []))
    listen.run(job2, tone(job2.dir / "upload.wav"), None)
    assert not (job2.dir / "story.wav").exists()
    assert "narrator voice" in job2.s["voice_note"]


def test_javanese_child_voice_falls_back_to_the_narrator_with_a_note():
    job = make_job(language="jv", narration_voice="child")
    listen.run(job, tone(job.dir / "upload.wav"), None)
    assert "narrator voice" in job.s["voice_note"]
    assert not (job.dir / "story.wav").exists()


def test_recordings_are_trimmed_to_the_configured_maximum(monkeypatch):
    from api.config import settings
    from api.pipeline import media

    monkeypatch.setattr(settings, "max_audio_seconds", 1)
    job = make_job()
    wav = media.to_wav(tone(job.dir / "long.wav", seconds=3.0), job.dir / "short.wav", max_seconds=settings.max_audio_seconds)
    assert media.wav_seconds(wav) <= 1.05
