"""Stage 6 - Animate. Muse Wonder is Meta's frontier agentic model (text output; Meta Model API has no
video-generation model as of Oct 2026). It acts as the dalang's hands: it looks at each storyboard frame,
reads the motion prompt and returns a keyframe motion plan for every puppet and the camera. Our kelir
engine then performs that plan into a moving clip with lamp flicker and wayang shadows."""
from __future__ import annotations

import json
import logging

from .. import cost, meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import MotionPlan, Scene, Script
from . import engine, scenes

log = logging.getLogger("dalang.animate")


def fallback_plan(scene: Scene) -> dict:
    """Rule-based motion used offline or if the model is unavailable: puppets glide in to their marks."""
    plan = scenes.staging_plan(scene)
    words = scene.motion_prompt.lower()
    for i, tr in enumerate(plan["puppets"]):
        kf = tr["keyframes"][0]
        x, face = kf["x"], kf["facing"]
        start = -0.2 if face == "right" else 1.2
        frames = [{"t": 0, "x": start if scene.n == 1 or "enter" in words or "in from" in words else x, "lift": 0,
                   "angle": 0, "facing": face},
                  {"t": 0.3, "x": x, "lift": 0, "angle": 0, "facing": face}]
        if any(w in words for w in ("jump", "hop", "lompat", "leap")):
            frames += [{"t": 0.55, "x": x + (0.08 if face == "right" else -0.08), "lift": 0.18, "angle": 8, "facing": face},
                       {"t": 0.75, "x": x + (0.12 if face == "right" else -0.12), "lift": 0, "angle": 0, "facing": face}]
        elif any(w in words for w in ("bow", "sembah", "greet")):
            frames += [{"t": 0.6, "x": x, "lift": 0, "angle": -10 if face == "right" else 10, "facing": face},
                       {"t": 0.85, "x": x, "lift": 0, "angle": 0, "facing": face}]
        elif any(w in words for w in ("fly", "terbang")):
            frames += [{"t": 0.6, "x": x, "lift": 0.2, "angle": 5, "facing": face}]
        tr["keyframes"] = frames
        tr["idle"] = "tremble" if scene.mood == "tense" and i == 0 else "sway"
    return plan


def plan_scene(job: Job, script: Script, scene: Scene) -> dict:
    """Muse Wonder looks at the scene's still and returns a keyframe motion plan (enter, sway, bow...) for each puppet; any puppet it leaves out gets a glide-in, and an unusable plan falls back to rule-based motion."""
    cast = ", ".join(f"{st.id} (starts at x={st.position:.2f}, facing {st.facing})" for st in scene.staging) or "none"
    content = [
        {"type": "text", "text": f"Scene {scene.n} of '{script.title}'. Mood: {scene.mood}. Duration about "
                                 f"{scene.duration_s:.0f} s.\nAction: {scene.action}\nMotion prompt: {scene.motion_prompt}\n"
                                 f"Puppets (use exactly these ids): {cast}\nNarration: {scene.narration}"},
        meta_client.image_part(job.dir / f"still_{scene.n}.jpg"),
    ]
    try:
        with cost.labelled(f"scene {scene.n}"):
            raw = meta_client.chat_json(
                [{"role": "system", "content": prompts.ANIMATE_SYSTEM}, {"role": "user", "content": content}],
                prompts.ANIMATE_SCHEMA, "motion_plan", model=settings.animate_model, reasoning_effort="medium")
        plan = MotionPlan(**raw)
        ids = {st.id for st in scene.staging}
        plan.puppets = [p for p in plan.puppets if p.id in ids]
        have = {p.id for p in plan.puppets}
        for tr in MotionPlan(**fallback_plan(scene)).puppets:  # never lose a puppet the script put on stage
            if tr.id not in have:
                plan.puppets.append(tr)
                cost.record_decision(f"scene {scene.n}: plan left out {tr.id}; added a glide-in so no puppet is lost",
                                     agent="animate")
        job.used(settings.animate_model)
        return plan.model_dump()
    except Exception as e:  # noqa: BLE001 - any failure falls back to rule-based motion
        log.warning("Muse Wonder plan failed for scene %s: %s", scene.n, e)
        cost.record_decision(f"scene {scene.n}: motion plan unusable ({str(e)[:80]}); rule-based glide used",
                             agent="animate")
        return fallback_plan(scene)


def run(job: Job, script: Script, only: set[int] | None = None) -> list[dict]:
    """only: re-plan just these scenes and reuse the saved motion plans of the others (Gara-gara re-render)."""
    job.stage("animate", "running", "Muse Wonder is directing the puppets...", clear_thumbs=True)
    plans = []
    S_W, S_H = 480, 270
    for scene in script.scenes:
        saved = job.dir / f"motion_{scene.n}.json"
        clip = job.dir / f"clip_{scene.n}.mp4"
        if only is not None and scene.n not in only and saved.exists():
            plans.append(json.loads(saved.read_text()))
            if clip.exists():
                job.stage("animate", thumb=job.url(clip))
                continue
            plan = plans[-1]
        else:
            job.stage("animate", detail=f"Muse Wonder is directing scene {scene.n}...")
            plan = plan_scene(job, script, scene)
            plans.append(plan)
            saved.write_text(json.dumps(plan, indent=1))
        # quick low-res preview clip for the progress screen
        film = engine.Film(S_W, S_H, style=job.s["style"], shots=[engine.Shot(
            duration=min(6.0, scene.duration_s), bg=engine.cover(job.dir / f"bg_{scene.n}.png", S_W, S_H, 1.1),
            plan=plan, mood=scene.mood)])
        kel = engine.Kelir(film, scenes.load_puppets(job, script, engine.ref_size(S_W, S_H)))
        engine.encode(kel, clip, fps=12)
        job.stage("animate", thumb=job.url(clip))
    job.set(motion=plans)
    fresh = len(plans) if only is None else len([n for n in only if n <= len(plans)])
    job.stage("animate", "done", f"{fresh} scenes choreographed" + ("" if only is None else f", {len(plans) - fresh} reused"))
    return plans
