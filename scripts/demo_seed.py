"""Make one complete film from the sample story and keep it as the DEMO_MODE fallback.

    python scripts/demo_seed.py                 # live Meta models (needs META_API_KEY); FAKE_META=1 for a free rehearsal
    python scripts/demo_seed.py --text "..."    # your own story text
    python scripts/demo_seed.py --audio story.m4a --language jv
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    runner,  # noqa: E402
    sample_stories,  # noqa: E402
)
from api.config import settings  # noqa: E402
from api.jobs import Job  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--language", default="id", choices=["id", "jv", "en"])
    ap.add_argument("--style", default="classic", choices=["classic", "colorful"])
    a = ap.parse_args()
    text = a.text if (a.text or a.audio) else sample_stories.KANCIL_ID
    audio = None
    if settings.mode == "not_configured":
        print("No META_API_KEY set. Set it for real models, or FAKE_META=1 for a labelled placeholder rehearsal.")
        sys.exit(1)
    job = Job.create(a.language, a.style, review=False)
    if a.audio:
        audio = job.dir / ("upload" + Path(a.audio).suffix)
        shutil.copyfile(a.audio, audio)
    print(f"Job {job.id} ({'fake Meta API (recorded fixtures)' if settings.fake_meta else 'LIVE Meta models'})")
    t0 = time.time()
    last = ""
    runner._front(job, audio, text)  # runs synchronously here
    for st in job.s["stages"]:
        line = f"  {st['label']:<24} {st['status']:<8} {st['detail']}"
        if line != last:
            print(line)
    print(f"status={job.s['status']} cost=${job.s['cost_usd']:.3f} time={time.time() - t0:.0f}s models={job.s['models']}")
    if job.s["status"] != "done":
        print("error:", job.s.get("error") or job.s.get("message"))
        sys.exit(1)
    demo = settings.data_dir / "demo"
    demo.mkdir(parents=True, exist_ok=True)
    for name in ("dalang_landscape.mp4", "dalang_vertical.mp4", "poster.jpg"):
        if (job.dir / name).exists():
            shutil.copyfile(job.dir / name, demo / name)
    (demo / "job.json").write_text(json.dumps({"title": job.s["title"], "script": job.s["script"],
                                               "offline": job.s.get("offline", True)}, indent=1))
    print(f"Saved demo film to {demo}")


if __name__ == "__main__":
    main()
