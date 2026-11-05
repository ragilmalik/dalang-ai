"""Character consistency: one score per film from the SAM 3.1 cut-out masks and the checker agent.

Dalang AI keeps a character the same in every scene by construction: SAM 3.1 cuts each puppet out ONCE and the
renderer reuses those exact pixels in every scene. This module measures how well that worked, per puppet:
  * mask source  - a SAM 3.1 mask (1.0), a Kotak Wayang puppet first cut by SAM (1.0), or the plain-background
                   fallback when SAM found nothing (0.6);
  * mask quality - silhouette fill inside its box (a puppet, not a speck or the whole sheet) and clean edges
                   (few half-transparent pixels);
  * checker      - the Muse Spark checker accepted the character sheet first time (1.0), each redraw -0.15;
  * same pixels  - the cut-out file the renderer used has the same SHA-256 as the one SAM produced (1 or 0),
                   across every scene the puppet appears in.
Score = mean of the four, x100. The film score is the mean over its puppets."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .. import cost
from ..jobs import Job
from ..schemas import Script

SOURCE_SCORE = {"sam": 1.0, "kotak": 1.0, "background": 0.6}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else ""


def mask_quality(path: Path) -> dict[str, float]:
    """fill: share of the trimmed cut-out that is puppet; soft: share of edge pixels that are half transparent."""
    a = np.asarray(Image.open(path).convert("RGBA").split()[-1], dtype=np.uint8)
    solid = a > 215
    some = a > 40
    area = max(1, int(some.sum()))
    fill = float(some.mean())
    soft = float((some & ~solid).sum()) / area
    fill_ok = 1.0 if 0.12 <= fill <= 0.92 else 0.5
    soft_ok = 1.0 if soft <= 0.2 else max(0.4, 1.0 - (soft - 0.2) * 2)
    return {"fill": round(fill, 3), "soft_edges": round(soft, 3), "score": round((fill_ok + soft_ok) / 2, 3)}


def measure(job: Job, script: Script) -> dict[str, Any]:
    """Score every cast puppet; called after casting (hashes recorded) and again after the final cut."""
    sources = job.s.get("cutouts") or {}
    old = {p["id"]: p for p in (job.s.get("consistency") or {}).get("puppets", [])}
    rows = []
    for c in job.s.get("cast", []):
        path = job.dir / "puppets" / f"{c['id']}.png"
        if not path.exists():
            continue
        source = "kotak" if c.get("returning") else sources.get(c["id"], "sam")
        q = mask_quality(path)
        checker = max(0.4, 1.0 - 0.15 * len(c.get("rejections") or []))
        digest = sha(path)
        first = old.get(c["id"], {}).get("sha") or digest
        same = 1.0 if digest == first else 0.0
        scenes_in = [s.n for s in script.scenes if c["id"] in s.characters]
        score = (SOURCE_SCORE.get(source, 0.6) + q["score"] + checker + same) / 4
        rows.append({"id": c["id"], "name": c["name"], "source": source, "fill": q["fill"],
                     "soft_edges": q["soft_edges"], "checker_redraws": len(c.get("rejections") or []),
                     "sha": first, "same_pixels": bool(same), "scenes": scenes_in, "score": round(score * 100)})
    film = round(sum(r["score"] for r in rows) / len(rows)) if rows else 0
    appearances = sum(len(r["scenes"]) for r in rows)
    out = {"score": film, "puppets": rows, "appearances": appearances,
           "method": "SAM 3.1 mask source + mask quality + checker agent + same cut-out pixels in every scene"}
    job.set(consistency=out)
    return out


def record(job: Job, script: Script, when: str) -> dict[str, Any]:
    out = measure(job, script)
    if out["puppets"]:
        sam = sum(1 for r in out["puppets"] if r["source"] in {"sam", "kotak"})
        same = all(r["same_pixels"] for r in out["puppets"])
        cost.record_decision(
            f"character consistency {out['score']}/100 {when}: {sam}/{len(out['puppets'])} puppets from SAM 3.1 masks, "
            f"{'same' if same else 'CHANGED'} cut-out pixels across {out['appearances']} scene appearances",
            agent="consistency")
    return out
