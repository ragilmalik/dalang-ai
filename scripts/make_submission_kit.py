"""Build the submission kit: ../deliverables/submission-kit/ and ../deliverables/submission-kit.zip

    python scripts/make_submission_kit.py
    python scripts/make_submission_kit.py --out /some/folder   # somewhere else

Layout:
  1-video/          demo video + captions + thumbnail + storyboard + voice-over + demo script
  2-images/         screenshots, demo GIF, share poster, architecture diagram, QR code
  3-sample-films/   the sample film (16:9 and 9:16), its poster, a printable-puppets PDF
  4-text/           submission form answers, write-up, submission text, checklists, testing and review kits
  5-launch/         X launch plan + the three 9:16 clips
  dalang-ai-source.zip   the code, from `git archive HEAD` (committed files only, no .env, no data/)
  README.txt        what every file is

It notes when the art is placeholder (made on the fake Meta API).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import qr  # noqa: E402

DOCS = ROOT / "docs"
DEMO_DATA = ROOT / "data" / "demo"
# the Kancil sample film made with the live Meta models (Nov 5), shipped in the repo; the demo seed is the fallback
LIVE_SAMPLE = ROOT / "content" / "samples" / "kancil-id"


def probe(p: Path) -> float:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return 0.0


def copy(src: Path, dst: Path, missing: list[str]) -> bool:
    if not src.exists():
        missing.append(str(src.relative_to(ROOT)))
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copyfile(src, dst)
    return True


def fake_art() -> bool:
    timeline = DOCS / "demo" / "timeline.json"
    if timeline.exists():
        return bool(json.loads(timeline.read_text()).get("recorded_in_fake_mode", True))
    return True


def sample_pdf(out: Path) -> bool:
    """Printable puppets for the sample film, rebuilt from the demo job if its folder is still there."""
    meta = DEMO_DATA / "job.json"
    if not meta.exists():
        return False
    from api import db, printable
    from api.config import settings

    for job_dir in sorted((settings.data_dir / "jobs").glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        state = db.load(job_dir.name)
        if state and state.get("status") == "done" and (job_dir / "puppets").exists() and state.get("cast"):
            printable.build(state, job_dir, out)
            return True
    return False


# The current site (docs/screenshots/ui/after, full pages made by web/e2e/ui_shots.py)
UI_SHOTS = ("home-phone", "home-desktop", "film-working-phone", "film-done-phone", "film-gara-phone", "kelir-phone",
            "vote-phone", "pentas-desktop", "watch-phone", "kotak-phone", "judge-desktop")
# Older captures that show something the full pages don't (the printable puppet PDF, the agent trace opened)
EARLIER_SHOTS = ("9-puppets-pdf.png", "10-agent-trace.png")  # kept the name; since Nov 6 these are live captures
WIN_KIT = ROOT.parent / "deliverables" / "win-kit"


def readme(mins: str, art_fake: bool, ph: int, size: str = "1920x1080", teasers: str = "60 s, 9:16 42 s") -> str:
    art = ("NOTE: everything was made on the built-in fake Meta API, so the art is PLACEHOLDER. After the Meta key is in\n"
           "      .env, run `python scripts/go_live.py` and then this script again to rebuild the kit with real art.\n"
           if art_fake else "Art: made with the live Meta models.\n")
    link = ("Live link: not deployed yet, so there is no QR in this kit (set PUBLIC_BASE_URL and rebuild).\n"
            if qr.is_placeholder() else f"QR / live link: {qr.base_url()} (2-images/qr.png)\n")
    return f"""DALANG AI - SUBMISSION KIT (Meta Global AI Developer Hackathon, Cerebral Valley)
Official deadline: Wed Nov 4, 9:00 PM ET = Thu Nov 5, 09:00 WIB (passed). Check Cerebral Valley for what can still change.

{art}{link}
1-video/          dalang-ai-demo.mp4 ({mins}, {size}, captions burned in, recorded on the current site, Kokoro voice-over) + .srt/.vtt captions, YouTube thumbnail,
                  teasers (16:9 {teasers}): teaser_60s.mp4 and teaser_vertical.mp4, cut from the same render,
                  STORYBOARD.md + storyboard.jpg (one still per shot), voiceover.txt, DEMO_SCRIPT.md, timeline.json.
                  Upload the mp4 to YouTube (unlisted is fine) and paste the link in the form.
                  The "tell" shot uploads assets/sample-story/sample_story_synthetic.mp3, a SYNTHETIC sample voice
                  (normal pitch; not a child, not a real person). Swap in a real recording: python scripts/go_live.py --audio real_story.m4a
2-images/         screenshots/top/ = the first screen of each main page on the current site (phone 390 px at 2x, desktop
                  1440 px): home, pipeline theatre, finished film, gara-gara, Kelir Live, classroom vote, watch, Pentas,
                  storyboard and the Penjaga Budaya / receipt panel. Best for the form and for X.
                  screenshots/full-page/ = the same pages as full-length captures (plus Kotak Wayang and judge mode).
                  screenshots/more/ = the printable puppet PDF and the agent trace opened (live models, Nov 6). Plus demo.gif, poster.jpg (share card), architecture.png (and qr.png once deployed).
3-sample-films/   The Kancil sample film (a story I wrote for the project, made with the live Meta models on Nov 5) in
                  16:9 and 9:16 (the 9:16 one is for X), its poster, and the printable puppets PDF.
4-text/           SUBMISSION_FORM.md = every form field with paste-ready answers. SUBMISSION.md = title, tagline,
                  description. WRITEUP.md = longer write-up. META_MODELS.md = how the Meta models are used. SUBMISSION_CHECKLIST.md and MALIK_CHECKLIST.md = steps.
                  USER_TESTING.md and CULTURAL_REVIEW.md = family-testing and cultural-review kits (no real sessions
                  or reviews yet). OPEN_WEIGHTS.md = Muse Spark Open + Muse Glimmer. VERIFICATION_REPORT.md,
                  TEST_REPORT.md, ACCESSIBILITY.md = check results. VOICES.md = how the narrator voices were picked.
                  DESIGN_SYSTEM.md = the look. JUDGE_ONE_PAGER.pdf = one A4 page for judges (link slots in brackets).
5-launch/         X_LAUNCH.md (day-by-day plan Nov 1-8, posts, #DalangCilik copy, alt text; nothing posted) and three
                  9:16 clips with captions (+ .srt).
dalang-ai-source.zip   The code from `git archive HEAD` (no .env, no data/).
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "deliverables" / "submission-kit"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    missing: list[str] = []

    v = out / "1-video"
    for name in ("dalang-ai-demo.mp4", "dalang-ai-demo.srt", "dalang-ai-demo.vtt", "thumbnail.jpg", "STORYBOARD.md",
                 "storyboard.jpg", "voiceover.txt", "timeline.json", "teaser_60s.mp4", "teaser_vertical.mp4"):
        copy(DOCS / "demo" / name, v / name, missing)
    copy(DOCS / "demo" / "storyboard", v / "storyboard", missing)
    copy(DOCS / "DEMO_SCRIPT.md", v / "DEMO_SCRIPT.md", missing)

    i = out / "2-images"
    shots = DOCS / "screenshots"
    for png in sorted((shots / "readme").glob("*.png")):
        copy(png, i / "screenshots" / "top" / png.name, missing)
    for name in UI_SHOTS:
        copy(shots / "ui" / "after" / f"{name}.png", i / "screenshots" / "full-page" / f"{name}.png", missing)
    for name in EARLIER_SHOTS:
        copy(shots / name, i / "screenshots" / "more" / name, missing)
    for name in ("demo.gif", "poster.jpg"):
        copy(shots / name, i / name, missing)
    copy(DOCS / "architecture.png", i / "architecture.png", missing)
    if not qr.is_placeholder():  # a QR only for a real, deployed link
        qr.save(qr.app_url(), i / "qr.png")

    f = out / "3-sample-films"
    films = LIVE_SAMPLE if (LIVE_SAMPLE / "dalang_landscape.mp4").exists() else DEMO_DATA
    copy(films / "dalang_landscape.mp4", f / "kancil-16x9.mp4", missing)
    copy(films / "dalang_vertical.mp4", f / "kancil-9x16-for-X.mp4", missing)
    copy(films / "poster.jpg", f / "kancil-poster.jpg", missing)
    if not sample_pdf(f / "kancil-puppets-to-print.pdf"):
        missing.append("printable puppets PDF (run scripts/demo_seed.py first)")

    t = out / "4-text"
    for name in ("SUBMISSION_FORM.md", "SUBMISSION.md", "WRITEUP.md", "SUBMISSION_CHECKLIST.md", "MALIK_CHECKLIST.md",
                 "USER_TESTING.md", "CULTURAL_REVIEW.md", "OPEN_WEIGHTS.md", "META_MODELS.md", "VERIFICATION_REPORT.md",
                 "TEST_REPORT.md", "ACCESSIBILITY.md", "VOICES.md", "DESIGN_SYSTEM.md"):
        copy(DOCS / name, t / name, missing)
    if (WIN_KIT / "JUDGE_ONE_PAGER.pdf").exists():
        copy(WIN_KIT / "JUDGE_ONE_PAGER.pdf", t / "JUDGE_ONE_PAGER.pdf", missing)

    lch = out / "5-launch"
    copy(DOCS / "X_LAUNCH.md", lch / "X_LAUNCH.md", missing)
    for clip in sorted((DOCS / "launch").glob("clip*")):
        copy(clip, lch / clip.name, missing)

    src = out / "dalang-ai-source.zip"
    r = subprocess.run(["git", "archive", "--format=zip", "--prefix=dalang-ai/", "-o", str(src), "HEAD"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        missing.append(f"source zip (git archive failed: {r.stderr.strip()[:120]})")

    secs = probe(v / "dalang-ai-demo.mp4")
    whole = round(secs)  # same rounding as docs/facts.json's demo_length
    mins = f"{whole // 60}:{whole % 60:02d}" if secs else "missing"
    try:
        size = str(json.loads((DOCS / "demo" / "timeline.json").read_text(encoding="utf-8")).get("size", "1920x1080"))
    except (OSError, ValueError):
        size = "1920x1080"
    tz = [probe(v / n) for n in ("teaser_60s.mp4", "teaser_vertical.mp4")]
    teasers = f"{tz[0]:.0f} s, 9:16 {tz[1]:.0f} s" if all(tz) else "60 s, 9:16 42 s"
    (out / "README.txt").write_text(readme(mins, fake_art(), 0, size, teasers), encoding="utf-8")

    zpath = out.parent / f"{out.name}.zip"
    zpath.unlink(missing_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out.parent))
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Kit: {out} ({files} files)")
    print(f"Zip: {zpath} ({zpath.stat().st_size / 1e6:.1f} MB)")
    print(f"Demo video: {mins}" + (" (placeholder art, fake Meta API)" if fake_art() else ""))
    if missing:
        print("MISSING (kit built without them):\n  - " + "\n  - ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
