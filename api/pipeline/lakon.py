"""Stage 2 - Lakon: transcript -> structured script. Muse Spark on Meta Model API, or Muse Spark Open
(open weights) on Baseten when USE_OPEN_WEIGHTS=true. Validated with pydantic, retried once."""
from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError

from .. import cost, meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import Script


def _cache_key(transcript: str, lang: str, engine: str) -> str:
    fake = "fake" if settings.fake_meta else "live"
    return hashlib.sha256(f"{fake}|{engine}|{lang}|{transcript.strip()}".encode()).hexdigest()[:24]


def run(job: Job, transcript: str) -> Script:
    """Stage 2, lakon: the transcript becomes a structured script (Muse Spark json_schema, or Muse Spark Open on Baseten with USE_OPEN_WEIGHTS). Validated with pydantic and retried once with the error; cached by transcript hash."""
    lang = job.s["language"]
    open_w = settings.open_weights_active
    engine = f"{settings.open_model} (open weights, Baseten)" if open_w else settings.lakon_model
    job.stage("lakon", "running", f"Ki Dalang is writing the lakon with {engine}...")
    cache = settings.data_dir / "cache" / "lakon"
    cache.mkdir(parents=True, exist_ok=True)
    returning = job.s.get("returning") or []
    back_ids = ",".join(sorted(p["id"] for p in returning))
    cf = cache / f"{_cache_key(transcript + ('|' + back_ids if back_ids else ''), lang, engine)}.json"
    script: Script | None
    if cf.exists():  # cost guard: same story, same script
        script = Script(**json.loads(cf.read_text()))
        cost.record_decision("same story told before: script reused from the transcript-hash cache", agent="cache")
    else:
        messages = [{"role": "system", "content": prompts.LAKON_SYSTEM},
                    {"role": "user", "content": prompts.lakon_user(transcript, lang, returning)}]
        script = None
        last_err = ""
        for attempt in range(2):  # spec §6: validate with pydantic, retry once
            msgs = messages if attempt == 0 else messages + [
                {"role": "user", "content": f"Your last JSON was invalid ({last_err}). Return valid JSON only."}]
            try:
                raw = meta_client.chat_json(msgs, prompts.LAKON_SCHEMA, "lakon",
                                            reasoning_effort="medium", open_weights=open_w)
                script = Script(**raw)
                break
            except (ValidationError, json.JSONDecodeError, KeyError, TypeError) as e:
                last_err = str(e)[:300]
                cost.record_decision(f"script failed Pydantic validation ({last_err[:100]}); asking again with the error",
                                     agent="lakon")
        if script is None:
            raise RuntimeError(f"The script came back invalid twice: {last_err}")
        cf.write_text(script.model_dump_json())
    assert script is not None
    script = keep_returning(script, returning)
    job.used(settings.open_model if open_w else settings.lakon_model)
    job.set(script=script.model_dump(), title=script.title)
    names = ", ".join(c.name for c in script.characters)
    job.stage("lakon", "done", f"\u201c{script.title}\u201d \u00b7 {len(script.scenes)} scenes \u00b7 {names}")
    return script


def polish(job: Job, script: Script) -> Script:
    """Title and moral polish on Muse Glimmer (open weights). Only when USE_OPEN_WEIGHTS=true; any failure
    keeps the original title and moral."""
    if not settings.glimmer_active:
        return script
    job.stage("lakon", detail=f"Polishing the title and moral with {settings.glimmer_model} (open weights)...")
    summary = " ".join(s.action for s in script.scenes)[:600]
    try:
        raw = meta_client.chat_json(
            [{"role": "system", "content": prompts.POLISH_SYSTEM},
             {"role": "user", "content": prompts.polish_user(script.title, script.moral, script.language, summary)}],
            prompts.POLISH_SCHEMA, "polish", glimmer=True)
        title, moral = str(raw.get("title", "")).strip(), str(raw.get("moral", "")).strip()
    except Exception as e:  # noqa: BLE001 - polish is optional
        job.stage("lakon", detail=f"Polish skipped ({str(e)[:80]})")
        return script
    if 2 <= len(title) <= 80:
        script.title = title
    if 4 <= len(moral) <= 200:
        script.moral = moral
    job.used(settings.glimmer_model)
    job.set(script=script.model_dump(), title=script.title, polished_by=settings.glimmer_model)
    return script


def keep_returning(script: Script, returning: list[dict]) -> Script:
    """Make sure every returning puppet is in the cast under its own id (matched by id, then by name), so casting
    reuses its cut-out. A returning puppet the model left out is added to the cast (and to scene 1 if there is room)."""
    if not returning:
        return script
    data = script.model_dump()
    chars = data["characters"]
    for p in returning:
        match = next((c for c in chars if c["id"] == p["char_id"]), None) or next(
            (c for c in chars if c["name"].strip().lower() == p["name"].strip().lower()), None)
        if match is not None:
            old = match["id"]
            match.update(id=p["char_id"], name=p["name"], visual_description=p["look"], kind=p["kind"])
            for sc in data["scenes"]:
                sc["characters"] = [p["char_id"] if c == old else c for c in sc["characters"]]
                for st in sc["staging"]:
                    if st["id"] == old:
                        st["id"] = p["char_id"]
        elif len(chars) < 4:
            chars.append({"id": p["char_id"], "name": p["name"], "role": "helper", "wayang_archetype": p["archetype"],
                          "visual_description": p["look"], "kind": p["kind"], "sam_phrase": p["sam_phrase"],
                          "cultural_note": p["note"]})
            if len(data["scenes"][0]["characters"]) < 3:
                data["scenes"][0]["characters"].append(p["char_id"])
    return Script(**data)
