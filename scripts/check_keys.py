"""Check that your real keys work, with a handful of tiny, cheap calls (about $0.03 in total).

    python scripts/check_keys.py            # Meta Model API: Muse Spark, Muse Wonder, Muse Image, SAM 3.1, Voice Transcribe
    python scripts/check_keys.py --no-image # skip the two paid image calls (Muse Image + SAM)

It reads the same .env file the app uses. Every check prints PASS or FAIL with the reason.
If Baseten is configured (BASETEN_API_KEY + USE_OPEN_WEIGHTS=true) it also checks Muse Spark Open, and with
USE_OPEN_WEIGHTS=true it checks Muse Glimmer (GLIMMER_API_KEY / TOGETHER_API_KEY, or a local GLIMMER_API_BASE).
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from api import meta_client  # noqa: E402
from api.config import settings  # noqa: E402

GREEN, RED, DIM, END = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        t0 = time.time()
        try:
            detail = fn() or ""
            results.append((name, True, f"{detail} ({time.time() - t0:.1f}s)"))
            print(f"{GREEN}PASS{END}  {name}  {DIM}{detail}{END}")
        except Exception as e:  # noqa: BLE001
            results.append((name, False, str(e)[:300]))
            print(f"{RED}FAIL{END}  {name}  {str(e)[:300]}")
        return fn
    return deco


def tone_wav(path: Path, seconds: float = 1.5, sr: int = 16000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / sr))) for i in range(int(sr * seconds)))
        w.writeframes(frames)
    return path


def puppet_png(path: Path) -> Path:
    im = Image.new("RGB", (512, 512), (240, 230, 210))
    d = ImageDraw.Draw(im)
    d.ellipse([170, 120, 340, 290], fill=(150, 60, 30))
    d.rectangle([220, 290, 290, 470], fill=(150, 60, 30))
    im.save(path)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-image", action="store_true", help="skip Muse Image and SAM 3.1 (the two paid image calls)")
    ap.add_argument("--self-test", action="store_true", help="run every check against the built-in fake API (no keys, no cost)")
    a = ap.parse_args()
    if a.self_test:
        settings.meta_api_key = settings.meta_api_key or "test-key"
        settings.fake_flag = True

    print("\nDalang AI key check\n" + "-" * 40)
    if not settings.meta_api_key:
        print(f"{RED}No META_API_KEY in .env{END}. Open the .env file, paste your Meta Model API key after "
              "META_API_KEY=, save, and run this again.")
        return 1
    if settings.fake_meta and not a.self_test:
        print(f"{RED}FAKE_META=1 (or MOCK=1) is set in .env{END}; set it to 0 to test the real API.")
        return 1
    print(f"Meta key: ...{settings.meta_api_key[-4:]}   base: {settings.meta_api_base}\n")
    tmp = Path(tempfile.mkdtemp())

    @check(f"Muse Spark ({settings.lakon_model}) structured output")
    def _spark():
        out = meta_client.chat_json([{"role": "user", "content": "Reply with ok=true."}],
                                    {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                                    "ping", reasoning_effort="low")
        assert out.get("ok") is True, out
        return "JSON schema reply OK"

    @check(f"Muse Wonder ({settings.animate_model})")
    def _wonder():
        out = meta_client.chat_json([{"role": "user", "content": "Reply with ok=true."}],
                                    {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                                    "ping", model=settings.animate_model, reasoning_effort="low")
        assert out.get("ok") is True, out
        return "JSON schema reply OK"

    @check(f"Muse Voice Transcribe ({settings.asr_model})")
    def _asr():
        text = meta_client.transcribe(tone_wav(tmp / "tone.wav"), 1.5, ["Indonesian"])
        return f"endpoint answered (transcript of a test tone: {text!r})"

    @check(f"Muse Spark audio for Javanese ({settings.audio_model})")
    def _audio():
        text = meta_client.transcribe_with_spark_audio(tone_wav(tmp / "tone2.wav"), "Javanese")
        return f"endpoint answered ({len(text)} chars)"

    if not a.no_image:
        @check(f"Muse Image ({settings.image_model})  ~$0.01")
        def _image():
            out = meta_client.generate_image("A small gold wayang kulit gunungan on a plain cream background, no text",
                                             tmp / "img.png", size="1024x1024", fast=True)
            w, h = Image.open(out).size
            return f"{w}x{h} PNG"

        @check(f"SAM 3.1 ({settings.sam_model})  ~$0.0025")
        def _sam():
            matches = meta_client.segment(puppet_png(tmp / "p.png"), "puppet")
            return f"{len(matches)} mask(s)"

    if settings.use_open_weights:
        @check(f"Muse Spark Open on Baseten ({settings.open_model})")
        def _open():
            if not settings.baseten_api_key:
                raise RuntimeError("USE_OPEN_WEIGHTS=true but BASETEN_API_KEY is empty")
            out = meta_client.chat_json([{"role": "user", "content": "Reply with ok=true."}],
                                        {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                                        "ping", reasoning_effort="low", open_weights=True)
            assert out.get("ok") is True, out
            return "open-weights model answered"

    if settings.use_open_weights:
        @check(f"Muse Glimmer, open weights ({settings.glimmer_model} at {settings.glimmer_api_base})")
        def _glimmer():
            if not settings.glimmer_active:
                raise RuntimeError("USE_OPEN_WEIGHTS=true but GLIMMER_API_KEY (or TOGETHER_API_KEY) is empty and "
                                   "GLIMMER_API_BASE is not a local server")
            out = meta_client.chat_json([{"role": "user", "content": "Reply with ok=true."}],
                                        {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                                        "ping", glimmer=True)
            assert out.get("ok") is True, out
            return "safety screen + title/moral polish will run on Muse Glimmer"

    @check("Narration voice (edge-tts, free)")
    def _tts():
        from api.pipeline import media

        out = media.narrate("Halo, ini Ki Dalang.", "id", tmp / "v.wav")
        if not out:
            raise RuntimeError("could not reach the voice service (films will still work, with subtitles only)")
        return f"{media.wav_seconds(out):.1f}s of speech"

    failed = [r for r in results if not r[1]]
    print("-" * 40)
    if failed:
        print(f"{RED}{len(failed)} of {len(results)} checks failed.{END} Fix the key or setting named above and run again.")
        return 1
    where = "against the built-in fake API (self-test)" if a.self_test else "Dalang AI is ready for live films."
    print(f"{GREEN}All {len(results)} checks passed {where}{END}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
