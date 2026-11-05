"""Copy finished sample films from a data folder into content/samples/ so they ship with the repo.

    python scripts/bundle_samples.py --data path/to/data        # every finished sample film in that data folder

The films are the three sample stories written for this project (api/samples.py), rendered by the live Meta models.
Files are made smaller on the way in so the repo stays light: videos re-encoded (h264 CRF 30), backdrops, character
sheets and rejected pictures stored as WebP, puppet cut-outs as smaller PNGs (they keep their names, because new
stories can reuse a puppet from the gallery). Files no page links to (per-scene clips, voice tracks) are left out.
The API copies content/samples/ into its data folder on start (api/samples.import_bundled).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "samples"
NOTE = ("Sample story written for this project. Pictures by Muse Image, puppets cut out by SAM 3.1, script, checks "
        "and motion by Muse Spark and Muse Wonder, all on the live Meta Model API ({date}). Narration: edge-tts.")


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def small_video(src: Path, dst: Path) -> None:
    ffmpeg("-i", str(src), "-c:v", "libx264", "-preset", "slow", "-crf", "30", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(dst))


def webp(src: Path, dst: Path, max_side: int = 1280) -> None:
    im = Image.open(src).convert("RGB")
    im.thumbnail((max_side, max_side))
    im.save(dst, "WEBP", quality=80, method=6)


def puppet_png(src: Path, dst: Path, max_side: int = 900) -> None:
    im = Image.open(src).convert("RGBA")
    im.thumbnail((max_side, max_side))
    im.save(dst, "PNG", optimize=True)


def bundle(state: dict, src_dir: Path, date: str) -> Path:
    key, jid = state["sample_key"], state["id"]
    dst = OUT / key
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    text = json.dumps(state)
    renames: dict[str, str] = {}
    for rel in sorted(set(re.findall(rf"/media/{jid}/([^?\"]+)", text))):
        src = src_dir / rel
        if not src.exists():
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith("clip_"):
            continue  # per-scene clips: no page needs them once the film is cut
        if rel.endswith(".mp4"):
            small_video(src, out)
        elif rel.startswith("puppets/"):
            puppet_png(src, out)
        elif rel.endswith(".png"):
            new = rel[:-4] + ".webp"
            webp(src, dst / new)
            renames[rel] = new
        else:
            shutil.copyfile(src, out)
    for old, new in renames.items():
        text = text.replace(f"/media/{jid}/{old}", f"/media/{jid}/{new}")
    text = re.sub(rf"(/media/{jid}/clip_\d+\.mp4)\?v=\d+", "", text)  # dropped clips: no link
    clean = json.loads(text)
    clean.update(public=True, sample=True, offline=False, bundled=True, sample_note=NOTE.format(date=date))
    (dst / "state.json").write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
    return dst


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="the data folder the samples were made in")
    ap.add_argument("--date", default="2026-11-05")
    a = ap.parse_args(argv)
    data = Path(a.data)
    rows = sqlite3.connect(data / "dalang.db").execute("SELECT data FROM jobs WHERE status='done'").fetchall()
    newest: dict[str, dict] = {}
    for (raw,) in rows:
        s = json.loads(raw)
        if s.get("sample") and s.get("sample_key") and not s.get("offline"):
            if s["sample_key"] not in newest or s["updated"] > newest[s["sample_key"]]["updated"]:
                newest[s["sample_key"]] = s
    if not newest:
        print("no finished live sample films in", data)
        return 1
    for key, s in sorted(newest.items()):
        d = bundle(s, data / "jobs" / s["id"], a.date)
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        print(f"{key:<16} {s['id']}  {s['title'][:40]:<40} {size / 1e6:5.1f} MB -> {d.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
