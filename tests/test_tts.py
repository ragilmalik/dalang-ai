"""Narration voice selection (TTS_ENGINE / TTS_VOICE_<LANG>), edge-tts fallback and loudness normalisation.
No model is loaded: the engines are replaced with stubs that write a short tone."""
from __future__ import annotations

import subprocess

import numpy as np
import pytest

from api import tts
from api.pipeline import media


def _tone(path, seconds=1.0, amp=0.05, sr=24000):
    t = np.arange(int(sr * seconds)) / sr
    media.write_wav(path, (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr)
    return path


@pytest.fixture
def engines(monkeypatch, tmp_path):
    """Stub every engine. calls records (engine, voice); engines in `broken` raise like a missing package."""
    calls: list[tuple[str, str]] = []
    broken: set[str] = set()

    def make(name):
        def fn(text, v, out):
            calls.append((name, v.voice))
            if name in broken:
                raise ModuleNotFoundError(f"No module named '{name}'")
            return _tone(out.with_name(out.stem + f".{name}.wav"))
        return fn

    monkeypatch.setattr(tts, "SYNTH", {k: make(k) for k in ("edge", "kokoro", "pocket", "mms")})
    for k in ("TTS_ENGINE", "TTS_VOICE_ID", "TTS_VOICE_JV", "TTS_VOICE_EN"):
        monkeypatch.delenv(k, raising=False)
    return calls, broken


def test_auto_covers_every_story_language():
    assert set(tts.AUTO) == set(tts.EDGE) == {"id", "jv", "en"}
    assert all(v.engine == "edge" for v in tts.EDGE.values())
    assert tts.EDGE["jv"].voice.startswith("jv-ID")  # Javanese keeps the Javanese voice (docs/VOICES.md)


def test_auto_defaults_are_the_shootout_winners():
    assert tts.AUTO["en"] == tts.Voice("kokoro", "af_heart", speed=0.92)  # falls back to EDGE["en"] when missing
    assert tts.AUTO["id"] == tts.EDGE["id"] == tts.Voice("edge", "en-US-EmmaMultilingualNeural", rate="-6%")
    assert tts.AUTO["jv"] == tts.Voice("edge", "jv-ID-SitiNeural", rate="-4%", pitch="+4Hz")


def test_default_english_falls_back_to_edge_without_kokoro(engines, tmp_path):
    calls, broken = engines
    broken.add("kokoro")
    got = tts.synth("Once upon a time.", "en", tmp_path / "n.wav")
    assert got is not None and got[1] == tts.EDGE["en"]
    assert calls == [("kokoro", "af_heart"), ("edge", tts.EDGE["en"].voice)]


def test_default_is_auto_and_unknown_language_reads_indonesian(engines):
    assert tts.pick("en") == tts.AUTO["en"]
    assert tts.pick("xx") == tts.AUTO["id"]


def test_engine_env_forces_edge_everywhere(engines, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "edge")
    assert all(tts.pick(lang).engine == "edge" for lang in ("id", "jv", "en"))


def test_engine_env_only_applies_where_the_engine_speaks_the_language(engines, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "kokoro")
    assert tts.pick("en").engine == "kokoro"
    assert tts.pick("jv") == tts.AUTO["jv"]  # Kokoro has no Javanese


def test_per_language_override(engines, monkeypatch):
    monkeypatch.setenv("TTS_VOICE_EN", "kokoro:am_michael")
    assert tts.pick("en") == tts.Voice("kokoro", "am_michael", speed=0.92)
    monkeypatch.setenv("TTS_VOICE_EN", "nonsense")
    assert tts.pick("en") == tts.AUTO["en"]


def test_unknown_engine_name_means_auto(engines, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "chatterbox-xl")
    assert tts.pick("id") == tts.AUTO["id"]


def test_missing_local_model_falls_back_to_edge(engines, monkeypatch, tmp_path):
    calls, broken = engines
    broken.add("kokoro")
    monkeypatch.setenv("TTS_ENGINE", "kokoro")
    got = tts.synth("Hello there.", "en", tmp_path / "n.wav")
    assert got is not None
    wav, voice = got
    assert voice == tts.EDGE["en"] and wav.exists()
    assert calls == [("kokoro", tts.KOKORO["en"].voice), ("edge", tts.EDGE["en"].voice)]
    assert not list(tmp_path.glob("*.kokoro.wav")) and not list(tmp_path.glob("*.edge.wav"))  # raw files cleaned


def test_local_model_used_when_installed(engines, monkeypatch, tmp_path):
    calls, _ = engines
    monkeypatch.setenv("TTS_VOICE_JV", "mms:facebook/mms-tts-jav")
    got = tts.synth("Sugeng enjing.", "jv", tmp_path / "n.wav")
    assert got and got[1].engine == "mms" and calls == [("mms", "facebook/mms-tts-jav")]


def test_no_voice_at_all_returns_none(engines, monkeypatch, tmp_path):
    _, broken = engines
    broken.update({"edge", "kokoro", "mms"})
    monkeypatch.setenv("TTS_ENGINE", "kokoro")
    assert tts.synth("Hello.", "en", tmp_path / "n.wav") is None
    assert media.narrate("Halo", "id", tmp_path / "m.wav") is None


def _lufs(path):
    p = subprocess.run([media.ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null",
                        "-"], capture_output=True, text=True)
    line = [x for x in p.stderr.splitlines() if x.strip().startswith("I:")][-1]
    return float(line.split()[1])


def test_narration_is_loudness_normalised(engines, tmp_path):
    out = media.narrate("Halo", "id", tmp_path / "n.wav")
    assert out is not None
    with __import__("wave").open(str(out), "rb") as w:
        assert w.getframerate() == media.SR and w.getnchannels() == 1
    quiet = _lufs(_tone(tmp_path / "quiet.wav"))  # the stub's raw level, about -32 LUFS
    assert quiet < -25 and abs(_lufs(out) - tts.TARGET_LUFS) < 1.5


def test_voice_name_follows_settings(engines, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "edge")
    assert media.voice_name("jv") == tts.EDGE["jv"].voice
    monkeypatch.setenv("TTS_VOICE_EN", "kokoro:af_heart")
    assert media.voice_name("en") == "af_heart (kokoro)"


def test_parse_voice_speed_and_rate():
    assert tts.parse_voice("kokoro:af_heart@0.95") == tts.Voice("kokoro", "af_heart", speed=0.95)
    assert tts.parse_voice("edge:en-GB-RyanNeural@-5") == tts.Voice("edge", "en-GB-RyanNeural", rate="-5%")
    assert tts.parse_voice("kokoro:af_heart@fast") is None
    assert tts.parse_voice("af_heart") is None


def test_local_engine_runs_in_tts_python_when_not_installed_here(monkeypatch, tmp_path):
    """No kokoro in this venv and TTS_PYTHON set: the line is rendered by that Python, not dropped."""
    import builtins

    real_import = builtins.__import__

    def no_kokoro(name, *a, **k):
        if name == "kokoro":
            raise ModuleNotFoundError("No module named 'kokoro'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_kokoro)
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, input=kw["input"], env=kw["env"])
        _tone(tmp_path / "n.raw.wav")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    monkeypatch.setenv("TTS_PYTHON", "/opt/tts-venv/bin/python")
    raw = tts._kokoro("Hello.", tts.Voice("kokoro", "af_heart", speed=0.92), tmp_path / "n.wav")
    assert raw.exists() and seen["cmd"][:3] == ["/opt/tts-venv/bin/python", "-m", "api.tts"]
    assert seen["input"] == "Hello." and "TTS_PYTHON" not in seen["env"]  # no loop back into itself


def test_local_engine_without_tts_python_is_a_missing_module(monkeypatch, tmp_path):
    monkeypatch.delenv("TTS_PYTHON", raising=False)
    with pytest.raises(ModuleNotFoundError):
        tts._other_python("Hello.", tts.Voice("kokoro", "af_heart"), tmp_path / "n.wav")


def test_batch_skips_edge_lines(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(tts.subprocess, "run", lambda *a, **k: called.append(a))
    tts.batch([("Hi.", tts.EDGE["en"], tmp_path / "a.wav")])
    assert not called


def test_prefetch_renders_local_lines_once_and_synth_uses_them(engines, monkeypatch, tmp_path):
    calls, _ = engines
    seen: list[list] = []

    def fake_batch(jobs):
        seen.append(jobs)
        for _text, _v, out in jobs:
            _tone(out)

    monkeypatch.setattr(tts, "batch", fake_batch)
    tts.prefetch(["One.", "Two.", "One.", ""], "en", tmp_path)
    assert len(seen) == 1 and [j[0] for j in seen[0]] == ["One.", "Two."]  # one model load, no duplicates
    got = tts.synth("Two.", "en", tmp_path / "n.wav")
    assert got and got[1] == tts.AUTO["en"] and calls == []  # nothing synthesised again
    assert not tts.cached(tmp_path, tts.AUTO["en"], "Two.").exists()  # the pre-rendered file is used up
    tts.prefetch(["Halo."], "id", tmp_path)  # edge-tts: nothing to pre-render
    assert len(seen) == 1


def test_prefetch_failure_never_stops_a_film(engines, monkeypatch, tmp_path):
    def boom(jobs):
        raise RuntimeError("no model")

    monkeypatch.setattr(tts, "batch", boom)
    tts.prefetch(["One."], "en", tmp_path)  # logs, doesn't raise
    assert tts.synth("One.", "en", tmp_path / "n.wav") is not None


def test_film_prefetches_every_line_before_the_opening_is_spoken(monkeypatch):
    """The opening line must come out of the one-load batch too, not be spoken alone first and rendered twice."""
    from api.config import settings
    from api.jobs import Job
    from api.pipeline import mock, narrate
    from api.schemas import Script

    s = Script(**mock.SAMPLE_SCRIPT)
    job = Job.create("id", "classic", True)
    monkeypatch.setattr(settings, "narration_voice", True)
    order: list[str] = []
    monkeypatch.setattr(tts, "prefetch", lambda texts, lang, folder: order.append(f"prefetch:{len(texts)}"))
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: order.append(out.name) or out)
    narrate.run(job, s)
    assert order[0] == f"prefetch:{len(s.scenes) + (1 if s.opening else 0)}"
    if s.opening:
        assert order[1] == "opening.wav"


# --- Pocket TTS (Kyutai, MIT): the demo narrator since Nov 6 ----------------------------------------------------
def test_pocket_voice_parses_and_is_english_only(engines, monkeypatch):
    assert tts.parse_voice("pocket:alba") == tts.Voice("pocket", "alba")
    monkeypatch.setenv("TTS_ENGINE", "pocket")
    assert tts.pick("en").engine == "pocket"
    assert tts.pick("id") == tts.AUTO["id"]  # Pocket TTS speaks no Indonesian


def test_pocket_engine_uses_the_package_when_it_is_installed(monkeypatch, tmp_path):
    import sys
    import types

    loads: list[str] = []

    class FakeModel:
        sample_rate = 24000

        @classmethod
        def load_model(cls):
            loads.append("model")
            return cls()

        def get_state_for_audio_prompt(self, voice):
            loads.append(voice)
            return {"voice": voice}

        def generate_audio(self, state, text):
            class T:
                def numpy(self_inner):
                    return (0.05 * np.sin(np.arange(2400) / 4)).astype(np.float32)
            return T()

    monkeypatch.setitem(sys.modules, "pocket_tts", types.SimpleNamespace(TTSModel=FakeModel))
    monkeypatch.setattr(tts, "_models", {})
    raw = tts._pocket("Hello.", tts.Voice("pocket", "alba"), tmp_path / "a.wav")
    raw2 = tts._pocket("Again.", tts.Voice("pocket", "alba"), tmp_path / "b.wav")
    assert raw.exists() and raw2.exists() and loads == ["model", "alba"]  # model and voice load once


def test_pocket_without_the_package_goes_to_tts_python(monkeypatch, tmp_path):
    import sys

    monkeypatch.setitem(sys.modules, "pocket_tts", None)  # import fails
    monkeypatch.delenv("TTS_PYTHON", raising=False)
    with pytest.raises(ModuleNotFoundError):
        tts._pocket("Hello.", tts.Voice("pocket", "alba"), tmp_path / "a.wav")
