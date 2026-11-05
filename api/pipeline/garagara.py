"""Gara-gara: optional interactive branching.

After scene 2 (or 3 in a 6-scene lakon) the film pauses. A puppet asks the child a question written by Muse Spark
(structured output: speaker, question, two suggested answers). The child answers by voice or taps an option;
Muse Spark rewrites the remaining scenes (structured output, validated with pydantic, retried once) and the
pipeline paints, animates and narrates only those scenes before the final cut of the whole film.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

from .. import meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import Scene, Script
from . import animate, engine, listen, media, narrate, scenes

log = logging.getLogger("dalang.garagara")


class Question(BaseModel):
    speaker: str
    question: str = Field(min_length=3, max_length=220)
    options: list[str] = Field(min_length=2, max_length=2)

    @field_validator("options")
    @classmethod
    def short(cls, v: list[str]) -> list[str]:
        return [o.strip()[:80] for o in v]


class Rewrite(BaseModel):
    moral: str = ""
    scenes: list[Scene] = Field(min_length=1, max_length=4)


def split_point(script: Script) -> int:
    """Pause after scene 2, or after scene 3 when the lakon has 6 scenes."""
    return 3 if len(script.scenes) >= 6 else 2


def ask(job: Job, script: Script, kept: int) -> Question:
    """Muse Spark writes the gara-gara question: a puppet on stage after scene `kept` asks the child what happens next, with two short options."""
    raw = meta_client.chat_json(
        [{"role": "system", "content": prompts.GARA_SYSTEM},
         {"role": "user", "content": prompts.gara_user(script.model_dump_json(), kept, script.language)}],
        prompts.GARA_SCHEMA, "gara_gara", model=settings.lakon_model, reasoning_effort="low")
    job.used(settings.lakon_model)
    q = Question(**raw)
    on_stage = {c for s in script.scenes[:kept] for c in s.characters}
    if q.speaker not in on_stage:
        q.speaker = script.scenes[kept - 1].characters[0] if script.scenes[kept - 1].characters else script.characters[0].id
    return q


def part_one(job: Job, script: Script, kept: int, q: Question) -> Path:
    """Render scenes 1..kept as a short film that ends on the question card (landscape, 854x480).
    Motion plans and narration are saved so the final cut reuses them instead of paying twice."""
    W, H = 854, 480
    plans, voices = [], []
    vdir = job.dir / "voice"
    vdir.mkdir(exist_ok=True)
    if settings.narration_voice and script.opening:
        media.narrate(script.opening, script.language, vdir / "opening.wav")
    for sc in script.scenes[:kept]:
        plan = animate.plan_scene(job, script, sc)
        (job.dir / f"motion_{sc.n}.json").write_text(json.dumps(plan, indent=1))
        plans.append(plan)
        voices.append(narrate.voice_for(job, script, sc))
    if settings.narration_voice:
        media.narrate(q.question, script.language, job.dir / "gara_question.wav")
    from . import cut  # local import: cut imports scenes, which this module also uses

    film = cut.build_film(job, script, plans, voices, W, H, scene_list=script.scenes[:kept],
                          end_title="Gara-gara!", end_sub=q.question, with_title=True)
    kel = engine.Kelir(film, scenes.load_puppets(job, script, engine.ref_size(W, H)))
    silent = job.dir / "_part1_silent.mp4"
    engine.encode(kel, silent, settings.fps)
    audio = engine.soundtrack(film, job.dir / "_part1.wav")
    out = job.dir / "dalang_part1.mp4"
    media.run(["-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
               "-movflags", "+faststart", str(out)])
    silent.unlink(missing_ok=True)
    audio.unlink(missing_ok=True)
    return out


def pause(job: Job, script: Script, kept: int) -> None:
    """Render part one, ask the gara-gara question and set the film to status 'choice' until the child answers."""
    job.stage("scenes", detail=f"Gara-gara! Ki Dalang pauses after scene {kept} to ask what happens next...")
    q = ask(job, script, kept)
    film = part_one(job, script, kept, q)
    speaker = next((c for c in job.s.get("cast", []) if c["id"] == q.speaker), None)
    qwav = job.dir / "gara_question.wav"
    gara = {**job.s.get("gara_gara", {}), "enabled": True, "after": kept, "speaker": q.speaker,
            "speaker_name": next((c.name for c in script.characters if c.id == q.speaker), q.speaker),
            "speaker_cutout": speaker["cutout"] if speaker else None, "question": q.question, "options": q.options,
            "question_audio": job.url(qwav) if qwav.exists() else None, "answer": None, "status": "waiting"}
    job.set(gara_gara=gara, part1=job.url(film))
    job.stage("scenes", "done", f"Scenes 1-{kept} ready · waiting for the child's gara-gara choice")
    job.set(status="choice")


def hear(job: Job, audio: Path | None, text: str | None) -> str:
    """The child's answer: typed/tapped text, or a voice answer through the same speech-to-text as the story.
    The recording is deleted right after transcription, and the answer passes the same safety screen."""
    lang = job.s["language"]
    if text and text.strip():
        answer = text.strip()[:200]
    elif audio is not None:
        wav = media.to_wav(audio, job.dir / "answer.wav", max_seconds=settings.max_audio_seconds)
        try:
            if lang == "jv":
                answer = meta_client.transcribe_with_spark_audio(wav, prompts.LANG_NAMES["jv"])
                job.used(settings.audio_model)
            else:
                answer = meta_client.transcribe(wav, media.wav_seconds(wav), prompts.ASR_BIAS.get(lang), listen.KEYWORDS)
                job.used(settings.asr_model)
        finally:
            wav.unlink(missing_ok=True)
            Path(audio).unlink(missing_ok=True)
        answer = answer.strip()[:200]
    else:
        raise ValueError("Send the child's answer as text or a recording.")
    if not answer:
        raise listen.Blocked({"id": "Jawabannya belum terdengar. Coba lagi, ya!", "jv": "Wangsulane durung keprungu.",
                              "en": "We couldn't hear the answer. Try again!"}.get(lang))
    listen.screen(job, answer, "Let's choose something else!")
    return answer


def rewrite(job: Job, script: Script, kept: int, question: str, answer: str) -> Script:
    """Muse Spark rewrites scenes kept+1.. in the lakon schema; validated as a whole Script, retried once."""
    msgs = [{"role": "system", "content": prompts.REWRITE_SYSTEM},
            {"role": "user", "content": prompts.rewrite_user(script.model_dump_json(), kept, len(script.scenes),
                                                              question, answer, script.language)}]
    last = ""
    for attempt in range(2):
        m = msgs if attempt == 0 else msgs + [{"role": "user", "content": f"Your last JSON was invalid ({last}). Return valid JSON only."}]
        try:
            raw = meta_client.chat_json(m, prompts.REWRITE_SCHEMA, "gara_gara_rewrite", model=settings.lakon_model,
                                        reasoning_effort="medium")
            rw = Rewrite(**raw)
            if not 4 <= kept + len(rw.scenes) <= 6:
                raise ValueError(f"{len(rw.scenes)} new scenes would make {kept + len(rw.scenes)} in total (need 4-6)")
            data = script.model_dump()
            data["scenes"] = data["scenes"][:kept] + [s.model_dump() for s in rw.scenes]
            data["moral"] = rw.moral or script.moral
            new = Script(**data)  # renumbers, drops unknown character ids, re-stages
            if not all(s.characters for s in new.scenes[kept:]):
                raise ValueError("a new scene has no existing character on stage")
            job.used(settings.lakon_model)
            return new
        except (ValidationError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            last = str(e)[:300]
            log.warning("Gara-gara rewrite invalid (attempt %s): %s", attempt + 1, last)
    raise RuntimeError(f"The gara-gara rewrite came back invalid twice: {last}")


def apply_choice(job: Job, audio: Path | None, text: str | None) -> set[int]:
    """Hear the answer, rewrite the rest of the lakon, paint only the new scenes. Returns the new scene numbers."""
    gara = dict(job.s["gara_gara"])
    kept = int(gara["after"])
    job.stage("lakon", "running", "Ki Dalang is listening to the gara-gara answer...")
    answer = hear(job, audio, text)
    gara.update(answer=answer, status="answered")
    job.set(gara_gara=gara)
    job.stage("lakon", detail=f"\u201c{answer}\u201d \u00b7 rewriting the rest of the lakon...")
    script = rewrite(job, Script(**job.s["script"]), kept, gara["question"], answer)
    fresh = set(range(kept + 1, len(script.scenes) + 1))
    from . import penjaga  # the rewritten scenes get the same cultural review before they are painted

    script = penjaga.run(job, script, only=fresh)
    job.set(script=script.model_dump(), fresh_scenes=sorted(fresh))
    job.stage("lakon", "done", f"Gara-gara: \u201c{answer}\u201d \u00b7 scenes {kept + 1}-{len(script.scenes)} rewritten")
    scenes.run(job, script, only=fresh)
    return fresh
