"""Stage 4 - Puppet cut-out: SAM 3.1 segments each puppet from its character sheet into a transparent PNG
that is reused in every scene. Same pixels in every scene = character consistency."""
from __future__ import annotations

import logging
from pathlib import Path

from .. import cost, meta_client
from ..config import settings
from ..jobs import Job
from . import puppet

log = logging.getLogger("dalang.segment")


KIND_NOUN = {"human": "person", "animal": "animal", "creature": "creature"}  # all found masks on live SAM 3.1


def queries(phrase: str, kind: str = "") -> list[str]:
    """Concept phrases to try, most specific first. On the live SAM 3.1 (2026-11-05) the plain noun ("deer",
    "mouse deer") finds a puppet on its sheet where the word "puppet" alone often finds nothing, so the phrase
    without "puppet" and then its head noun ("golden snail princess" -> "princess") are tried, then a plain noun for the
    character's kind ("person", "animal", "creature"; on 2026-11-05 these found the princess, Kancil and Buto Ijo where
    "princess" and "puppet" did not), then the bare word."""
    out: list[str] = []
    bare = " ".join(w for w in phrase.split() if w.lower() not in {"puppet", "wayang"}).strip()
    last = bare.split()[-1] if bare else ""  # the head noun: "golden snail princess" -> "princess"
    for q in (phrase.strip(), bare, last, KIND_NOUN.get(kind, ""), "puppet"):
        if q and q not in out:
            out.append(q)
    return out


def cut_puppet(job: Job, sheet: Path, phrase: str, pid: str, kind: str = "") -> Path:
    """SAM 3.1 segments the puppet from its character sheet (by the script's phrase, then 'puppet') into a transparent PNG; with no usable mask it is cut out by the plain background instead."""
    out_dir = job.dir / "puppets"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{pid}.png"
    result = None
    for query in queries(phrase, kind):
        try:
            matches = meta_client.segment(sheet, query)
            job.used(settings.sam_model)
        except cost.BudgetExceeded:
            raise
        except Exception as e:  # keep the film going; fall back to a background key
            log.warning("SAM failed for %s (%s)", pid, e)
            matches = []
        result = puppet.cutout_from_sam(sheet, matches, out)
        if result:
            break
        if query != "puppet":
            cost.record_decision(f"SAM found no usable mask for \"{query}\"; trying a plainer phrase", agent="cutout")
    if result is None:
        cost.record_decision(f"no SAM mask for {pid}; cut out by the plain background instead", agent="cutout")
        puppet.cutout_by_background(sheet, out)
    job.set(cutouts={**(job.s.get("cutouts") or {}), pid: "sam" if result is not None else "background"})
    return out
