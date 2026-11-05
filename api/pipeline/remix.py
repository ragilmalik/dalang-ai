"""Remix: re-tell a finished film in another of the three languages, or from the villain's point of view, reusing
the same drawn puppets, backdrops, motion plans and Director plan. Only the words are new: one Muse Spark call
re-writes title, moral, opening and narration (json_schema `remix`), Penjaga Budaya reviews it, then narration and
the final cut run again. No Muse Image, SAM or Muse Wonder call is made.
"""
from __future__ import annotations

import shutil

from pydantic import BaseModel, Field

from .. import cost, meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import Script
from . import animate, cut, narrate, penjaga

COPY_GLOBS = ("bg_*.png", "still_*.jpg", "motion_*.json", "clip_*.mp4", "director.json")
COPY_DIRS = ("puppets", "sheets")


class RemixLine(BaseModel):
    n: int
    narration: str = Field(min_length=1)


class RemixText(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    moral: str = Field("", max_length=300)
    opening: str = Field("", max_length=300)
    scenes: list[RemixLine]


class RemixError(ValueError):
    pass


def villain_of(script: Script) -> str | None:
    v = next((c for c in script.characters if c.role == "villain"), None)
    return v.id if v else None


def create(src: Job, language: str, pov: str) -> Job:
    """Make the remix job (files copied, nothing generated yet). Raises RemixError for a request that cannot work."""
    if src.s["status"] != "done" or not src.s.get("script"):
        raise RemixError("Only a finished film can be remixed.")
    if language not in prompts.LANG_NAMES:
        raise RemixError("language must be id, jv or en")
    if pov not in ("original", "villain"):
        raise RemixError("pov must be original or villain")
    script = Script(**src.s["script"])
    if pov == "original" and language == script.language:
        raise RemixError("Pick another language or the villain's point of view.")
    vid = villain_of(script) if pov == "villain" else None
    if pov == "villain" and not vid:
        raise RemixError("This story has no villain to tell it.")
    vname = next((c.name for c in script.characters if c.id == vid), None)
    job = Job.create(language, src.s["style"], False, narration_voice="tts", remix_of=src.id,
                     remix={"language": language, "pov": pov, "villain": vname},
                     family=src.s.get("family"))
    for pat in COPY_GLOBS:
        for f in src.dir.glob(pat):
            shutil.copyfile(f, job.dir / f.name)
    for d in COPY_DIRS:
        if (src.dir / d).is_dir():
            shutil.copytree(src.dir / d, job.dir / d, dirs_exist_ok=True)
    cast = [{**c, "sheet": job.url(job.dir / "sheets" / f"{c['id']}.png"),
             "cutout": job.url(job.dir / "puppets" / f"{c['id']}.png")} for c in src.s.get("cast") or []]
    cards = [{**c, "still": job.url(job.dir / f"still_{c['n']}.jpg"), "backdrop": job.url(job.dir / f"bg_{c['n']}.png"),
              "rejections": []} for c in src.s.get("scenes") or []]
    job.set(script=script.model_dump(), cast=cast, scenes=cards, director=src.s.get("director"),
            cutouts=src.s.get("cutouts"), title=src.s.get("title"))
    src.set(remixes=[*(src.s.get("remixes") or []), job.id])
    return job


def rescript(job: Job, script: Script) -> Script:
    """One Muse Spark call: the same scenes in new words. Validated; a bad answer is asked again once."""
    pov = (job.s.get("remix") or {}).get("villain")
    lang = job.s["language"]
    msgs = [{"role": "system", "content": prompts.REMIX_SYSTEM},
            {"role": "user", "content": prompts.remix_user(script.model_dump_json(), lang, pov)}]
    last: Exception | None = None
    for attempt in range(2):
        raw = meta_client.chat_json(msgs, prompts.REMIX_SCHEMA, "remix", model=settings.lakon_model,
                                    reasoning_effort="medium", purpose="Remix: re-tell the film in new words")
        job.used(settings.lakon_model)
        try:
            text = RemixText(**raw)
            lines = {ln.n: ln.narration.strip()[:300] for ln in text.scenes}
            missing = [sc.n for sc in script.scenes if sc.n not in lines]
            if missing:
                raise RemixError(f"no narration for scene(s) {missing}")
            new = script.model_copy(deep=True)
            new.language = lang
            new.title, new.moral, new.opening = text.title.strip(), text.moral.strip(), text.opening.strip()
            for sc in new.scenes:
                sc.narration = lines[sc.n]
            return new
        except (ValueError, TypeError) as e:
            last = e
            if attempt == 0:
                cost.record_decision(f"remix answer unusable ({str(e)[:80]}); asked again", agent="remix")
                msgs = msgs + [{"role": "user", "content": f"Your answer was not usable: {str(e)[:200]}. Try again, "
                                                           "one narration per scene number."}]
    raise RemixError(f"The remix could not be written: {last}")


def run(job: Job) -> None:
    """Remix pipeline: reuse pictures, re-write the words, narrate and cut."""
    for key in ("listen", "casting", "scenes"):
        job.stage(key, "done", "reused from the original film")
    job.set(status="running")
    job.stage("lakon", "running", "Ki Dalang is re-telling the story...")
    script = rescript(job, Script(**job.s["script"]))
    script = penjaga.run(job, script)
    r = job.s.get("remix") or {}
    how = f"told by {r['villain']}" if r.get("villain") else f"in {prompts.LANG_NAMES[job.s['language']]}"
    cost.record_decision(f"remix {how}: same puppets, backdrops and motion; only the words are new "
                         "(no Muse Image, SAM or Muse Wonder call)", agent="remix")
    job.set(script=script.model_dump(), title=script.title,
            scenes=[{**c, "narration": next(s.narration for s in script.scenes if s.n == c["n"])}
                    for c in job.s.get("scenes") or []])
    job.stage("lakon", "done", f"Re-told {how}")
    job.set(status="rendering")
    plans = animate.run(job, script, only=set())  # every saved motion plan is reused
    voices = narrate.run(job, script)
    vids = cut.run(job, script, plans, voices)
    from .. import storage

    urls = {k: storage.publish(job, v) for k, v in vids.items()}
    poster = job.dir / "poster.jpg"
    job.set(status="done", videos=urls, poster=job.url(poster) if poster.exists() else None)
