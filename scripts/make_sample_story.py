"""Re-create the sample story recording: a SYNTHETIC sample voice made for this project (not a real person).

    python scripts/make_sample_story.py

Writes assets/sample-story/sample_story_synthetic.mp3: the sample kancil story (written for this project) read by the
edge-tts voice id-ID-GadisNeural at its normal pitch. It shows the voice path (upload a recording, Muse Voice
Transcribe hears it). To use a real recording instead (with consent, no names spoken):
    python scripts/go_live.py --audio path/to/real_story.m4a
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import sample_stories  # noqa: E402

OUT = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"
VOICE, PITCH, RATE = "id-ID-GadisNeural", "+0Hz", "+0%"  # synthetic sample voice, normal pitch


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", VOICE, f"--pitch={PITCH}", f"--rate={RATE}",
                        "--text", sample_stories.KANCIL_ID, "--write-media", str(OUT)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-400:])
        return 1
    print(f"wrote {OUT} (synthetic sample voice, not a real person)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
