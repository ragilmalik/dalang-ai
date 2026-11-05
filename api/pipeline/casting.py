"""Stage 3 - Casting: Muse Image draws one canonical wayang puppet per character (character sheet),
checked by the verify agent. Stage 4 (segment.py) then cuts each one out with SAM 3.1."""
from __future__ import annotations

from .. import cost, kotak, meta_client, prompts, resilience
from ..config import settings
from ..jobs import Job
from ..schemas import Script
from . import consistency, segment, verify


def run(job: Job, script: Script) -> None:
    """Stage 3, casting: one Muse Image character sheet per puppet (verified by the checker, redrawn on failure), cut out with SAM 3.1 into a transparent puppet reused in every scene. Puppets kept in the family's Kotak Wayang are brought back instead of redrawn."""
    style = job.s["style"]
    sheets = job.dir / "sheets"
    sheets.mkdir(exist_ok=True)
    job.stage("casting", "running", "Carving the puppets...", clear_thumbs=True)
    cast = []
    back = {p["char_id"]: p for p in job.s.get("returning") or []}
    for c in script.characters:
        sheet = sheets / f"{c.id}.png"
        if c.id in back and kotak.bring_into_job(back[c.id], job.dir, c.id):
            # Kotak Wayang: the family's own puppet comes back; no new Muse Image drawing or SAM cut
            job.stage("casting", detail=f"{c.name} comes back from the Kotak Wayang...")
            cost.record_decision(f"{c.name} comes back from the Kotak Wayang: no new Muse Image drawing or SAM cut",
                                 agent="kotak")
            cut = job.dir / "puppets" / f"{c.id}.png"
            cast.append({"id": c.id, "name": c.name, "sheet": job.url(sheet), "cutout": job.url(cut),
                         "rejections": [], "returning": True})
            job.set(cast=cast)
            job.stage("casting", thumb=job.url(cut))
            continue
        job.stage("casting", detail=f"Muse Image is drawing {c.name}...")
        rec = verify.make_verified(
            job, "casting", c.name, prompts.puppet_prompt(c.name, c.wayang_archetype, c.visual_description, style),
            sheet, must_show=f"exactly one full-body wayang kulit puppet of {c.name} ({c.visual_description}) "
                             "facing right on a plain background, no text",
            size="1024x1536")
        job.stage("casting", detail=f"SAM 3.1 is cutting out {c.name}...")
        cut = segment.cut_puppet(job, sheet, c.sam_phrase, c.id, c.kind)
        cast.append({"id": c.id, "name": c.name, "sheet": job.url(sheet), "cutout": job.url(cut),
                     "rejections": rec.get("rejections", []), "placeholder": bool(rec.get("placeholder"))})
        job.set(cast=cast)
        job.stage("casting", thumb=job.url(cut))

    # The gunungan (tree-of-life puppet) opens the film and sweeps between scenes.
    g_sheet = sheets / "gunungan.png"
    with cost.labelled("gunungan"):
        try:
            verify.cached_generate(prompts.GUNUNGAN_PROMPT, g_sheet, "1024x1536")
        except meta_client.MetaAPIError as e:
            from . import mock

            mock.gunungan(g_sheet)
            resilience.fallback(job, "casting", "gunungan", f"gunungan: Muse Image unavailable ({str(e)[:60]}); "
                                                           "the built-in gunungan drawing is used")
    segment.cut_puppet(job, g_sheet, "gunungan puppet", "gunungan")
    how = "cut out with SAM 3.1" + (" (fake API: placeholder art)" if settings.fake_meta else "")
    reused = sum(1 for c in cast if c.get("returning"))
    extra = f", {reused} back from the Kotak Wayang" if reused else ""
    consistency.record(job, script, "after casting")
    job.stage("casting", "done", f"{len(cast) - reused} puppets carved, {how}{extra}")
