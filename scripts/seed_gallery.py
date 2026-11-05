"""Fill the gallery with the three labelled sample films (Kancil in Bahasa Indonesia, Timun Mas in Basa Jawa,
The Golden Snail in English). Skips samples that are already there.

    python scripts/seed_gallery.py          # real Meta models (needs META_API_KEY; costs money)
    python scripts/seed_gallery.py --fake   # fake Meta API: free, labelled placeholder art (tests, offline)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="real Meta models (the default when META_API_KEY is set)")
    ap.add_argument("--fake", action="store_true", help="fake Meta API: free, labelled placeholder art (tests, offline)")
    a = ap.parse_args(argv)
    if a.fake:
        os.environ["FAKE_META"] = "1"  # before api.config is imported
    from api import samples
    from api.config import settings

    if settings.mode == "not_configured":
        print("No META_API_KEY set: set it to make the samples with the real models, or pass --fake.")
        return 1

    print(f"Seeding sample films on {'the fake Meta API (placeholder art)' if settings.fake_meta else 'LIVE Meta models'}")
    made = samples.seed()
    for job in made:
        print(f"  {job.s.get('sample_key'):<16} {job.id}  {job.s['status']:<6} {job.s['title']}")
    if not made:
        print("  all samples already in the gallery")
    return 0 if all(j.s["status"] == "done" for j in made) else 1


if __name__ == "__main__":
    sys.exit(main())
