"""Gara-gara building blocks without running the pipeline: who asks, how the answer is heard, how the rewrite is
validated and retried. Also the polish step and the sample-seeding thread."""
import copy
import json
import math
import struct
import wave
from pathlib import Path

import pytest

from api import meta_client, samples
from api.config import settings
from api.jobs import Job
from api.pipeline import garagara, lakon, listen, mock
from api.schemas import Script


def script() -> Script:
    return Script(**copy.deepcopy(mock.SAMPLE_SCRIPT))


def job(lang="id") -> Job:
    return Job.create(lang, "classic", False)


def tone(path: Path, seconds=1.5, sr=16000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 300 * i / sr))) for i in range(int(sr * seconds))))
    return path


# ----------------------------------------------------------------------------- split point and ask
def test_split_point_is_after_scene_two_or_three_for_six_scene_lakon():
    s = script()
    assert garagara.split_point(s) == (3 if len(s.scenes) >= 6 else 2)
    six = s.model_copy(update={"scenes": [s.scenes[0]] * 6})
    assert garagara.split_point(six) == 3
    four = s.model_copy(update={"scenes": [s.scenes[0]] * 4})
    assert garagara.split_point(four) == 2


def test_question_options_are_trimmed_and_exactly_two():
    q = garagara.Question(speaker="kancil", question="Apa lagi?", options=["  " + "x" * 120 + "  ", "b"])
    assert len(q.options[0]) == 80 and q.options[1] == "b"
    with pytest.raises(Exception):  # noqa: B017
        garagara.Question(speaker="kancil", question="Apa lagi?", options=["only one"])


def test_ask_moves_an_absent_speaker_onto_the_stage(monkeypatch):
    s = script()
    on_stage = s.scenes[1].characters[0]
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"speaker": "ghost", "question": "Lalu bagaimana?",
                                                                    "options": ["a", "b"]})
    q = garagara.ask(job(), s, 2)
    assert q.speaker == on_stage


def test_ask_falls_back_to_first_character_when_the_scene_is_empty(monkeypatch):
    s = script()
    s.scenes[1].characters = []
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"speaker": "ghost", "question": "Lalu bagaimana?",
                                                                    "options": ["a", "b"]})
    q = garagara.ask(job(), s, 2)
    assert q.speaker in {c.id for c in s.characters}


def test_ask_keeps_a_speaker_who_is_on_stage(monkeypatch):
    s = script()
    who = s.scenes[0].characters[0]
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"speaker": who, "question": "Lalu bagaimana?",
                                                                    "options": ["a", "b"]})
    assert garagara.ask(job(), s, 2).speaker == who


# ----------------------------------------------------------------------------- hear
def test_typed_answer_is_trimmed_to_200_characters():
    j = job("en")
    out = garagara.hear(j, None, "  " + "kind " * 80 + "  ")
    assert 0 < len(out) <= 200 and not out.startswith(" ")


def test_no_answer_at_all_is_a_value_error():
    with pytest.raises(ValueError):
        garagara.hear(job(), None, "   ")


def test_voice_answer_in_indonesian_goes_through_asr_and_the_recording_is_deleted(tmp_path):
    j = job("id")
    rec = tone(tmp_path / "ans.wav")
    out = garagara.hear(j, rec, None)
    assert out.strip() and not rec.exists()
    assert not (j.dir / "answer.wav").exists()


def test_voice_answer_in_javanese_uses_spark_audio(tmp_path, monkeypatch):
    seen = {}

    def fake(wav, name):
        seen["name"] = name
        return "  Kancil nulung baya  "

    monkeypatch.setattr(meta_client, "transcribe_with_spark_audio", fake)
    j = job("jv")
    rec = tone(tmp_path / "ans.wav")
    assert garagara.hear(j, rec, None) == "Kancil nulung baya"
    assert seen["name"] and not rec.exists()


def test_silent_answer_is_a_kind_block_in_the_childs_language(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_client, "transcribe", lambda *a, **k: "   ")
    for lang, word in (("id", "Jawabannya"), ("en", "couldn't hear")):
        with pytest.raises(listen.Blocked) as e:
            garagara.hear(job(lang), tone(tmp_path / f"{lang}.wav"), None)
        assert word in str(e.value)


def test_unsafe_answer_is_blocked_by_the_same_screen():
    with pytest.raises(listen.Blocked):
        garagara.hear(job(), None, "ceritakan tentang perang dan bom")


# ----------------------------------------------------------------------------- rewrite
def rewrite_payload(n_scenes=2, kept=2):
    sc = copy.deepcopy(mock.SAMPLE_SCRIPT["scenes"][kept:kept + n_scenes])
    return {"moral": "", "scenes": sc}


def test_rewrite_keeps_the_old_moral_when_the_new_one_is_blank(monkeypatch):
    s = script()
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: rewrite_payload())
    new = garagara.rewrite(job(), s, 2, "q?", "a")
    assert new.moral == s.moral and [x.n for x in new.scenes] == list(range(1, len(new.scenes) + 1))
    assert new.scenes[:2] == s.scenes[:2]


def test_rewrite_retries_once_then_succeeds(monkeypatch):
    calls = []

    def flaky(msgs, schema, name, **k):
        calls.append(msgs)
        return {"scenes": "not a list"} if len(calls) == 1 else rewrite_payload()

    monkeypatch.setattr(meta_client, "chat_json", flaky)
    new = garagara.rewrite(job(), script(), 2, "q?", "a")
    assert len(calls) == 2 and "invalid" in calls[1][-1]["content"] and new.scenes


def test_rewrite_gives_up_after_two_invalid_answers(monkeypatch):
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"scenes": []})
    with pytest.raises(RuntimeError, match="invalid twice"):
        garagara.rewrite(job(), script(), 2, "q?", "a")


def test_rewrite_rejects_too_few_total_scenes(monkeypatch):
    s = script()
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: rewrite_payload(n_scenes=1, kept=2))
    with pytest.raises(RuntimeError):  # 2 kept + 1 new = 3 scenes, below the 4-scene minimum
        garagara.rewrite(job(), s, 2, "q?", "a")


def test_rewrite_rejects_a_scene_with_nobody_on_stage(monkeypatch):
    payload = rewrite_payload()
    for sc in payload["scenes"]:
        sc["characters"] = ["nobody-here"]
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: payload)
    with pytest.raises(RuntimeError):
        garagara.rewrite(job(), script(), 2, "q?", "a")


# ----------------------------------------------------------------------------- polish (Muse Glimmer)
def test_polish_is_off_without_open_weights():
    assert not settings.glimmer_active  # tests run with USE_OPEN_WEIGHTS=0
    s = script()
    title = s.title
    assert lakon.polish(job(), s).title == title


def test_polish_failure_keeps_title_and_moral(monkeypatch):
    s = script()
    title, moral = s.title, s.moral
    monkeypatch.setattr(type(settings), "glimmer_active", property(lambda self: True))

    def boom(*a, **k):
        raise RuntimeError("glimmer down")

    monkeypatch.setattr(meta_client, "chat_json", boom)
    j = job()
    out = lakon.polish(j, s)
    assert (out.title, out.moral) == (title, moral)


def test_polish_applies_valid_title_and_moral_only(monkeypatch):
    monkeypatch.setattr(type(settings), "glimmer_active", property(lambda self: True))
    s = script()
    old_moral = s.moral
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"title": "Kancil dan Buaya Sakti", "moral": "x"})
    out = lakon.polish(job(), s)
    assert out.title == "Kancil dan Buaya Sakti" and out.moral == old_moral  # a 1-letter moral is refused
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"title": "T" * 120, "moral": "Be kind to everyone"})
    out2 = lakon.polish(job(), s)
    assert out2.title == "Kancil dan Buaya Sakti" and out2.moral == "Be kind to everyone"


# ----------------------------------------------------------------------------- sample seeding thread
def test_seed_in_background_runs_seed_on_a_daemon_thread(monkeypatch):
    ran = []
    monkeypatch.setattr(samples, "seed", lambda *a, **k: ran.append(1))
    t = samples.seed_in_background()
    t.join(5)
    assert ran == [1] and t.daemon and t.name == "seed-samples"


def test_script_fixture_round_trips_through_json():
    assert Script(**json.loads(script().model_dump_json())).title == mock.SAMPLE_SCRIPT["title"]
