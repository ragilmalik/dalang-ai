"""Sample films for the gallery, so a fresh install does not open on an empty wall.

Three stories written for this project, in three languages and both styles: Kancil (Bahasa Indonesia, classic),
Timun Mas (Basa Jawa, colorful) and The Golden Snail (English, classic). Every sample is marked ``sample: true``
and the gallery and watch page label it "Contoh · Sample".

The repo ships these three films as made by the live Meta models on 2026-11-05 (content/samples/, written by
scripts/bundle_samples.py). On start the API copies them into its data folder once (BUNDLED_SAMPLES=0 turns
that off). Re-making them:

    python scripts/seed_gallery.py --live   # real Meta models (costs money)
    python scripts/seed_gallery.py          # fake Meta API: free, labelled placeholder art (tests, offline)
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Any

from . import db, sample_stories
from .config import ROOT, settings
from .jobs import Job

log = logging.getLogger("dalang.samples")

SAMPLES: list[dict[str, Any]] = [
    {"key": "kancil-id", "language": "id", "style": "classic", "text": sample_stories.KANCIL_ID},
    {"key": "timun-mas-jv", "language": "jv", "style": "colorful", "text": sample_stories.TIMUN_MAS_JV},
    {"key": "golden-snail-en", "language": "en", "style": "classic", "text": sample_stories.GOLDEN_SNAIL_EN},
]


def existing() -> set[str]:
    """Sample keys already finished and public in the gallery."""
    return {j.get("sample_key", "") for j in db.gallery(limit=500) if j.get("sample")}


def make(spec: dict[str, Any]) -> Job:
    """Run the whole pipeline for one sample story (synchronously) and publish it as a labelled sample."""
    from . import runner  # late import: runner pulls in the whole pipeline

    job = Job.create(spec["language"], spec["style"], review=False, sample=True, sample_key=spec["key"])
    runner._front(job, None, spec["text"])
    if job.s["status"] == "done":
        job.set(public=True)
    return job


def seed(only_missing: bool = True) -> list[Job]:
    """Make every sample that is not in the gallery yet. Returns the jobs it ran."""
    have = existing() if only_missing else set()
    made = []
    for spec in SAMPLES:
        if spec["key"] in have:
            continue
        job = make(spec)
        log.info("sample %s -> %s (%s)", spec["key"], job.id, job.s["status"])
        made.append(job)
    return made


def seed_in_background() -> threading.Thread:
    """Used by the API on startup when SEED_SAMPLES=1; the app answers requests while the samples render."""
    t = threading.Thread(target=seed, name="seed-samples", daemon=True)
    t.start()
    return t


BUNDLE = ROOT / "content" / "samples"


def bundled(root: Path = BUNDLE) -> list[dict[str, Any]]:
    """The sample films shipped in the repo (one folder per sample with state.json and its media files)."""
    out = []
    for f in sorted(root.glob("*/state.json")):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("bad bundled sample %s", f)
            continue
        if state.get("id") and state.get("status") == "done":
            out.append(state)
    return out


def import_bundled(root: Path = BUNDLE) -> list[str]:
    """Copy the shipped sample films into the data folder, once each. Returns the ids it added."""
    added = []
    for state in bundled(root):
        jid = state["id"]
        if db.load(jid):
            continue
        src = root / state["sample_key"]
        dst = settings.data_dir / "jobs" / jid
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("state.json"))
        db.save({**state, "public": True})
        added.append(jid)
    if added:
        log.info("bundled sample films added to the gallery: %s", ", ".join(added))
    return added
