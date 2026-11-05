"""ffmpeg helpers and narration voice."""
from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
import tempfile
import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np

log = logging.getLogger("dalang.media")

SR = 24000  # Muse Voice Transcribe native rate; also our audio mix rate


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:  # bundled binary, so Windows users don't need to install ffmpeg
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover
        raise RuntimeError("ffmpeg not found. Run: pip install imageio-ffmpeg") from e


@contextlib.contextmanager
def staged(out: Path) -> Iterator[Path]:
    """Where ffmpeg should write `out`. With ENCODE_DIR set (a local disk), it writes there and the finished file is
    moved into place afterwards: on some network filesystems ffmpeg's mp4 trailer / faststart rewrite fails with
    "Input/output error". Without ENCODE_DIR it writes `out` directly."""
    enc = os.environ.get("ENCODE_DIR", "").strip()
    if not enc:
        yield out
        return
    Path(enc).mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=out.suffix, dir=enc)
    os.close(fd)
    try:
        yield Path(tmp)
        shutil.move(tmp, out)
    finally:
        Path(tmp).unlink(missing_ok=True)


def run(args: list[str]) -> None:
    out = Path(args[-1]) if args and args[-1].endswith((".mp4", ".webm")) else None
    if out is None:
        p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    else:
        with staged(out) as dst:
            p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args[:-1], str(dst)],
                               capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {p.stderr[-800:]}")
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr[-800:]}")


def to_wav(src: Path, dst: Path, sr: int = SR, max_seconds: float | None = None) -> Path:
    """Any audio (webm/m4a/mp3/ogg/wav) -> mono 16-bit PCM WAV (the format the ASR endpoint wants).
    max_seconds trims longer recordings (a story is up to 90 s; this caps transcription cost and time)."""
    trim = ["-t", f"{max_seconds:g}"] if max_seconds else []
    run(["-i", str(src), *trim, "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", "-map_metadata", "-1", str(dst)])
    return dst


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return data


def write_wav(path: Path, samples: np.ndarray, sr: int = SR) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


# The narrator's voice: api/tts.py picks the engine per language (TTS_ENGINE) and falls back to edge-tts.
# Meta Model API has no text-to-speech model, so narration audio comes from there.
def voice_name(language: str) -> str:
    """The voice that narrates `language` under the current settings (TTS_ENGINE / TTS_VOICE_<LANG>)."""
    from .. import tts

    return tts.pick(language).label()


def narrate(text: str, language: str, out_wav: Path) -> Path | None:
    """Speak one scene's narration (24 kHz mono, -16 LUFS). Returns None if no voice is reachable."""
    from .. import tts

    got = tts.synth(text, language, out_wav, sr=SR)
    return got[0] if got else None


def gong(seconds: float = 3.5, base: float = 82.0) -> np.ndarray:
    """A synthesised gamelan-style gong hit (inharmonic partials, slow decay, gentle beat)."""
    t = np.arange(int(SR * seconds)) / SR
    partials = [(1.0, 1.0), (2.76, 0.45), (5.4, 0.2), (1.006, 0.6)]  # last one beats against the first (ombak)
    s = sum(a * np.sin(2 * np.pi * base * r * t) for r, a in partials)
    env = np.exp(-t * 1.3) * (1 - np.exp(-t * 60))
    return (s * env * 0.22).astype(np.float32)


def bonang(freq: float, seconds: float = 0.9) -> np.ndarray:
    t = np.arange(int(SR * seconds)) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2.01 * t)
    return (s * np.exp(-t * 5.5) * 0.12).astype(np.float32)


# slendro-ish pentatonic (Hz), used for a soft bonang pattern under the title card
SLENDRO = [293.0, 336.0, 386.0, 444.0, 510.0]
