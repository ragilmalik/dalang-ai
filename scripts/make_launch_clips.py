"""Render three short 9:16 clips (15-30 s) with captions for the X launch, from the sample film.

    python scripts/make_launch_clips.py                      # uses data/demo/dalang_vertical.mp4 (demo_seed.py makes it)
    python scripts/make_launch_clips.py path/to/vertical.mp4

Writes docs/launch/clip1-hook.mp4, clip2-dalang-hands.mp4, clip3-dalang-cilik.mp4 and a matching .srt for each.
While the film was made on the fake Meta API, every clip carries a small "placeholder art" label so nobody mistakes
it for the final Muse Image art. Re-run after go_live.py to get clips with the real art (the label disappears).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "launch"
FONT = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Bold.ttf") if Path(p).exists()), "")

# (file, start s, length s, captions [(from, to, text)])
CLIPS = [
    ("clip1-hook", 0.0, 22.0, [
        (0.0, 5.0, "A child tells a story out loud..."),
        (5.0, 11.0, "...and gets it back as a Javanese wayang kulit film"),
        (11.0, 17.0, "Ki Dalang opens the show: \"Kocap kacarita...\""),
        (17.0, 22.0, "Dalang AI  #DalangCilik"),
    ]),
    ("clip2-dalang-hands", 20.0, 20.0, [
        (0.0, 6.0, "Muse Image paints every puppet once"),
        (6.0, 12.0, "SAM 3.1 cuts it out, so it stays the same in every scene"),
        (12.0, 20.0, "Muse Wonder moves the puppets like a dalang's hands"),
    ]),
    ("clip3-dalang-cilik", -18.0, 18.0, [
        (0.0, 6.0, "Every child can be a dalang"),
        (6.0, 12.0, "Print the puppets, grab a torch, play shadows at home"),
        (12.0, 18.0, "Tell your story  #DalangCilik"),
    ]),
]


def probe(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def placeholder_art() -> bool:
    meta = ROOT / "data" / "demo" / "job.json"
    if meta.exists():
        return bool(json.loads(meta.read_text()).get("offline", True))
    from api.config import settings

    return settings.fake_meta


def render(src: Path, name: str, start: float, length: float, caps: list[tuple[float, float, str]], label: bool) -> Path:
    total = probe(src)
    start = max(0.0, total + start) if start < 0 else min(start, max(0.0, total - length))
    length = min(length, total - start)
    font = f"fontfile='{FONT}':" if FONT else ""
    filters = ["scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black"]
    tmp = Path(tempfile.mkdtemp(prefix="dalang-clip-"))
    for k, (a, b, text) in enumerate(caps):
        tf = tmp / f"{name}_{k}.txt"
        tf.write_text("\n".join(textwrap.wrap(text, 24)), encoding="utf-8")  # 720 px wide: about 24 chars a line
        filters.append(f"drawtext={font}textfile='{tf}':fontsize=38:line_spacing=10:fontcolor=0xFFE7B8:box=1:"
                       f"boxcolor=0x1b0f07@0.72:boxborderw=18:x=(w-text_w)/2:y=100:"
                       f"enable='between(t,{a},{min(b, length)})'")
    if label:
        filters.append(f"drawtext={font}text='placeholder art (no Meta key yet)':fontsize=22:fontcolor=white@0.85:"
                       "box=1:boxcolor=0x9d2b1e@0.8:boxborderw=8:x=w-text_w-24:y=h-60")
    out = OUT / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(src),
                    "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)], check=True)
    srt = [f"{i}\n{srt_time(a)} --> {srt_time(min(b, length))}\n{text}\n" for i, (a, b, text) in enumerate(caps, 1)]
    out.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    src = Path(argv[0]) if argv else ROOT / "data" / "demo" / "dalang_vertical.mp4"
    if not src.exists():
        print(f"{src} not found. Run: python scripts/demo_seed.py   (it makes the sample film)")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    label = placeholder_art()
    for name, start, length, caps in CLIPS:
        out = render(src, name, start, length, caps, label)
        print(f"wrote {out.relative_to(ROOT)} ({probe(out):.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
