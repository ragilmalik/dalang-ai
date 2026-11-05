"""Narration voices: pick a text-to-speech engine per language, fall back to edge-tts, loudness-normalise.

Meta Model API has no text-to-speech model, so the narrator's voice comes from here. Engines:

* ``edge``: the edge-tts client for Microsoft Edge's read-aloud voices (free, online, no weights). Always there.
* ``kokoro``: Kokoro-82M (hexgrad, Apache-2.0), an open model that runs on a laptop CPU. English only.
  Optional: ``pip install -r requirements-tts.txt`` (adds torch + kokoro, about 1 GB with the weights).
* ``mms``: Meta's MMS-TTS open models (facebook/mms-tts-ind / mms-tts-jav, CC-BY-NC-4.0, so non-commercial
  use only). Optional, same requirements file. Never the default.

``TTS_ENGINE`` picks the engine: ``auto`` (default) uses the per-language choice in ``AUTO`` below, which came
out of the voice shoot-out in docs/VOICES.md; ``edge``, ``kokoro`` or ``mms`` force one engine for every language
it can speak. ``TTS_VOICE_<LANG>`` (for example ``TTS_VOICE_EN=kokoro:am_michael``) overrides one language.
Whatever is picked, a missing package, missing weights or any synthesis error falls back to edge-tts, so
Docker and CI work without the heavy extras. Every line is normalised to -16 LUFS before it is mixed.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("dalang.tts")

TARGET_LUFS = -16.0


@dataclass(frozen=True)
class Voice:
    engine: str  # edge | kokoro | mms
    voice: str  # edge voice name, kokoro voice id, or MMS repo id
    rate: str = "+0%"  # edge only
    pitch: str = "+0Hz"  # edge only
    speed: float = 1.0  # kokoro / mms

    def label(self) -> str:
        return self.voice if self.engine == "edge" else f"{self.voice} ({self.engine})"


# Plain edge-tts voices: the fallback for every language, and what TTS_ENGINE=edge uses. The best edge voice per
# language in the Nov 2 shoot-out (docs/VOICES.md). Emma Multilingual reads Indonesian more naturally than the
# Indonesian voice (Gadis) and Whisper still hears every word. For Javanese the multilingual voices could not be
# checked (Whisper can't transcribe Javanese) and risk an Indonesian accent, so Siti stays, a little faster and higher.
EDGE = {
    "id": Voice("edge", "en-US-EmmaMultilingualNeural", rate="-6%"),
    "jv": Voice("edge", "jv-ID-SitiNeural", rate="-4%", pitch="+4Hz"),
    "en": Voice("edge", "en-US-EmmaMultilingualNeural", rate="-6%"),
}
# TTS_ENGINE=auto (default): the shoot-out winners. English uses Kokoro when it is installed, else edge.
AUTO = {**EDGE, "en": Voice("kokoro", "af_heart", speed=0.92)}
# What each optional engine can speak when it is forced with TTS_ENGINE.
KOKORO = {"en": Voice("kokoro", "af_heart", speed=0.92)}
MMS = {"id": Voice("mms", "facebook/mms-tts-ind"), "jv": Voice("mms", "facebook/mms-tts-jav")}
ENGINES = {"edge": EDGE, "kokoro": KOKORO, "mms": MMS}


def parse_voice(spec: str) -> Voice | None:
    """'kokoro:am_michael', 'kokoro:af_heart@0.95', 'edge:en-US-AvaMultilingualNeural', 'mms:facebook/mms-tts-ind'
    -> Voice. '@x' sets the speed (kokoro, mms) or, for edge, the rate in percent ('edge:en-GB-RyanNeural@-5')."""
    engine, _, name = spec.strip().partition(":")
    name, _, tune = name.partition("@")
    if engine not in ENGINES or not name:
        return None
    try:
        if engine == "edge":
            return Voice("edge", name, rate=f"{int(tune):+d}%" if tune else "-6%")
        return Voice(engine, name, speed=float(tune) if tune else (0.92 if engine == "kokoro" else 1.0))
    except ValueError:
        return None


def pick(language: str) -> Voice:
    """The voice for one language, from TTS_VOICE_<LANG>, then TTS_ENGINE, then AUTO."""
    lang = language if language in EDGE else "id"
    override = parse_voice(os.environ.get(f"TTS_VOICE_{lang.upper()}", ""))
    if override:
        return override
    engine = os.environ.get("TTS_ENGINE", "auto").strip().lower() or "auto"
    if engine in ENGINES:
        return ENGINES[engine].get(lang, AUTO[lang])
    return AUTO[lang]


# ---- engines: each writes a wav/mp3 file or raises -------------------------------------------------------------

def _edge(text: str, v: Voice, out: Path) -> Path:
    """edge-tts to an mp3. Retries once in a subprocess without proxy settings (some corporate proxies break it)."""
    mp3 = out.with_suffix(".mp3")
    try:
        import edge_tts

        async def _go() -> None:
            await edge_tts.Communicate(text, v.voice, rate=v.rate, pitch=v.pitch).save(str(mp3))

        asyncio.run(_go())
    except Exception as first:
        env = {k: val for k, val in os.environ.items() if "proxy" not in k.lower()}
        p = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", v.voice, f"--rate={v.rate}",
                            f"--pitch={v.pitch}", "--text", text, "--write-media", str(mp3)],
                           capture_output=True, text=True, env=env, timeout=90)
        if p.returncode != 0 or not mp3.exists():
            raise RuntimeError(f"edge-tts unavailable: {first}") from first
    return mp3


_lock = threading.Lock()
_models: dict[str, Any] = {}


def _other_python(text: str, v: Voice, out: Path) -> Path:
    """Run a local engine in the Python named by TTS_PYTHON (a separate venv with requirements-tts.txt), so the
    app's own environment stays light. Loads the model per call, so it suits short jobs like the demo voice-over."""
    py = os.environ.get("TTS_PYTHON", "")
    if not py:
        raise ModuleNotFoundError(f"{v.engine} is not installed (pip install -r requirements-tts.txt, or set TTS_PYTHON)")
    raw = out.with_name(out.stem + ".raw.wav")
    p = subprocess.run([py, "-m", "api.tts", v.engine, v.voice, str(v.speed), str(raw)], input=text, text=True,
                       capture_output=True, cwd=str(Path(__file__).resolve().parents[1]), timeout=600,
                       env={k: val for k, val in os.environ.items() if k != "TTS_PYTHON"})
    if p.returncode != 0 or not raw.exists():
        raise RuntimeError(f"{v.engine} via TTS_PYTHON failed: {p.stderr[-300:]}")
    return raw


def _kokoro(text: str, v: Voice, out: Path) -> Path:
    try:
        import soundfile as sf
        from kokoro import KPipeline  # optional: requirements-tts.txt
    except ImportError:
        return _other_python(text, v, out)

    lang = v.voice[0]  # a = American English, b = British English
    with _lock:
        pipe = _models.get(f"kokoro:{lang}")
        if pipe is None:
            pipe = _models[f"kokoro:{lang}"] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
        chunks = [np.asarray(a, dtype=np.float32) for _, _, a in pipe(text, voice=v.voice, speed=v.speed)]
    if not chunks:
        raise RuntimeError("kokoro returned no audio")
    raw = out.with_name(out.stem + ".raw.wav")
    sf.write(str(raw), np.concatenate(chunks), 24000)
    return raw


def _mms(text: str, v: Voice, out: Path) -> Path:
    try:
        import soundfile as sf
        import torch
        from transformers import AutoTokenizer, VitsModel  # optional: requirements-tts.txt
    except ImportError:
        return _other_python(text, v, out)

    with _lock:
        pair = _models.get(f"mms:{v.voice}")
        if pair is None:
            pair = _models[f"mms:{v.voice}"] = (AutoTokenizer.from_pretrained(v.voice),
                                                VitsModel.from_pretrained(v.voice).eval())
        tok, model = pair
        model.speaking_rate = v.speed
        torch.manual_seed(0)
        with torch.no_grad():
            wav = model(**tok(text.lower(), return_tensors="pt")).waveform[0].numpy()
    raw = out.with_name(out.stem + ".raw.wav")
    sf.write(str(raw), wav, model.config.sampling_rate)
    return raw


SYNTH = {"edge": _edge, "kokoro": _kokoro, "mms": _mms}


def loudnorm_filter(lufs: float = TARGET_LUFS) -> str:
    return f"loudnorm=I={lufs:g}:TP=-1.5:LRA=11"


def finish(src: Path, out_wav: Path, sr: int = 24000) -> Path:
    """Any engine output -> mono 16-bit wav at `sr`, loudness-normalised to TARGET_LUFS."""
    from .pipeline import media

    media.run(["-i", str(src), "-af", loudnorm_filter(), "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le",
               "-map_metadata", "-1", str(out_wav)])
    return out_wav


def speak(text: str, voices: list[Voice], out_wav: Path, sr: int = 24000) -> tuple[Path, Voice] | None:
    """Try each voice in turn; the first that works writes out_wav (mono, `sr`, TARGET_LUFS)."""
    for n, v in enumerate(voices):
        try:
            raw = SYNTH[v.engine](text, v, out_wav)
        except Exception as e:  # missing optional package or weights, offline, model error
            log.warning("Voice %s unavailable (%s)%s", v.label(), e, "; trying the next one" if n < len(voices) - 1 else "")
            continue
        try:
            finish(raw, out_wav, sr)
            return out_wav, v
        except Exception as e:
            log.warning("Could not decode audio from %s (%s)", v.label(), e)
        finally:
            if raw != out_wav:
                raw.unlink(missing_ok=True)
    return None


def cached(folder: Path, v: Voice, text: str) -> Path:
    """Where prefetch() leaves a pre-rendered raw line for (voice, text) in `folder`."""
    import hashlib

    return folder / f".tts_{hashlib.sha1(f'{v}|{text}'.encode()).hexdigest()[:16]}.wav"


def prefetch(texts: list[str], language: str, folder: Path) -> None:
    """Render a film's lines with a local engine in one model load (batch), so synth() finds them ready.
    Nothing to do for edge-tts. Anything that fails here is simply synthesised (or falls back) line by line."""
    v = pick(language)
    if v.engine == "edge":
        return
    try:
        batch([(t, v, cached(folder, v, t)) for t in dict.fromkeys(texts) if t and not cached(folder, v, t).exists()])
    except Exception as e:  # never let the prefetch stop a film
        log.warning("Voice prefetch with %s failed (%s)", v.label(), e)


def synth(text: str, language: str, out_wav: Path, sr: int = 24000) -> tuple[Path, Voice] | None:
    """Speak one narration line: the picked voice, then the edge-tts voice for the language.
    Returns (wav, the voice that spoke) or None when no voice is reachable (the film keeps its subtitles)."""
    first = pick(language)
    ready = cached(out_wav.parent, first, text)
    if ready.exists():
        try:
            return finish(ready, out_wav, sr), first
        except Exception as e:
            log.warning("Could not decode the pre-rendered line (%s)", e)
        finally:
            ready.unlink(missing_ok=True)
    fallback = EDGE.get(language, EDGE["id"])
    return speak(text, [first] if first == fallback else [first, fallback], out_wav, sr)


def _importable(engine: str) -> bool:
    import importlib.util

    need = {"kokoro": ("kokoro", "soundfile"), "mms": ("transformers", "torch", "soundfile")}.get(engine, ())
    return all(importlib.util.find_spec(m) is not None for m in need)


def batch(jobs: list[tuple[str, Voice, Path]]) -> None:
    """Pre-render many lines with local engines in one go (one model load). Writes each raw wav that works;
    the caller treats a missing file as 'not spoken'. Uses TTS_PYTHON when the engine isn't installed here."""
    local = [(t, v, o) for t, v, o in jobs if v.engine != "edge"]
    if not local:
        return
    here = [j for j in local if _importable(j[1].engine)]
    for text, v, out in here:
        try:
            Path(SYNTH[v.engine](text, v, out.with_name(out.stem + ".tmp.wav"))).replace(out)
        except Exception as e:
            log.warning("Voice %s failed on %r (%s)", v.label(), text[:40], e)
    away = [j for j in local if j not in here]
    py = os.environ.get("TTS_PYTHON", "")
    if away and py:
        import json

        spec = json.dumps([{"text": t, "engine": v.engine, "voice": v.voice, "speed": v.speed, "out": str(o)}
                           for t, v, o in away])
        p = subprocess.run([py, "-m", "api.tts", "--batch"], input=spec, text=True, capture_output=True,
                           cwd=str(Path(__file__).resolve().parents[1]), timeout=3600,
                           env={k: val for k, val in os.environ.items() if k != "TTS_PYTHON"})
        if p.returncode != 0:
            log.warning("TTS_PYTHON batch failed: %s", p.stderr[-300:])


if __name__ == "__main__":  # used through TTS_PYTHON:  python -m api.tts <engine> <voice> <speed> <out.wav>  (text on
    # stdin), or  python -m api.tts --batch  (JSON list of {text, engine, voice, speed, out} on stdin)
    import json

    if sys.argv[1] == "--batch":
        batch([(j["text"], Voice(j["engine"], j["voice"], speed=float(j["speed"])), Path(j["out"]))
               for j in json.loads(sys.stdin.read())])
    else:
        _engine, _voice, _speed, _out = sys.argv[1:5]
        _raw = SYNTH[_engine](sys.stdin.read(), Voice(_engine, _voice, speed=float(_speed)),
                             Path(_out).with_name(Path(_out).stem + ".tmp.wav"))
        Path(_raw).replace(_out)
