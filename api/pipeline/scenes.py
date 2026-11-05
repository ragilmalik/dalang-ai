"""Stage 5 - Scenes: Muse Image paints each backdrop (verified by the checker agent), then the SAM-cut
puppets are composited on their marks to make the storyboard still."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .. import cost, prompts
from ..jobs import Job
from ..schemas import Scene, Script
from . import engine, verify


def staging_plan(scene: Scene) -> dict:
    """A still 'motion plan' that just holds each puppet on its mark (used for storyboards and fallbacks)."""
    return {"camera": {"zoom_from": 1.0, "zoom_to": 1.06, "pan_x": 0.0, "pan_y": 0.0}, "lamp_flicker": 0.4,
            "puppets": [{"id": st.id, "idle": "sway", "keyframes": [{"t": 0, "x": st.position, "lift": 0, "angle": 0,
                                                                     "facing": st.facing}]} for st in scene.staging]}


def load_puppets(job: Job, script: Script, S: int) -> dict[str, engine.Puppet]:
    """The job's cut-out puppets, scaled for a frame of reference size S."""
    out = {}
    for c in script.characters:
        p = job.dir / "puppets" / f"{c.id}.png"
        if p.exists():
            out[c.id] = engine.load_puppet(p, c.kind, S)
    return out


def storyboard_still(job: Job, script: Script, scene: Scene, out: Path, W: int = 960, H: int = 540) -> Path:
    """One composited frame (backdrop + puppets on the kelir) for the storyboard card and for Muse Wonder to look at."""
    bg = job.dir / f"bg_{scene.n}.png"
    film = engine.Film(W, H, style=job.s["style"], shots=[engine.Shot(
        duration=1.0, bg=engine.cover(bg, W, H, 1.1), plan=staging_plan(scene), mood=scene.mood)])
    kel = engine.Kelir(film, load_puppets(job, script, engine.ref_size(W, H)))
    kel.shot_frame(film.shots[0], 0.0).convert("RGB").save(out, quality=88)
    return out


def paint_one(job: Job, script: Script, scene: Scene) -> dict:
    """Paint one empty backdrop with Muse Image through the verify -> redraw loop, composite the still, return its storyboard card."""
    bg = job.dir / f"bg_{scene.n}.png"
    rec = verify.make_verified(
        job, "scenes", f"scene {scene.n}", prompts.backdrop_prompt(scene.image_prompt, scene.mood, job.s["style"]),
        bg, must_show=f"an EMPTY wayang-style backdrop (no people, animals or puppets): {scene.setting}",
        context=scene.action)
    still = storyboard_still(job, script, scene, job.dir / f"still_{scene.n}.jpg")
    return {"n": scene.n, "narration": scene.narration, "setting": scene.setting, "still": job.url(still),
            "backdrop": job.url(bg), "attempts": rec["attempts"], "rejections": rec["rejections"],
            "placeholder": bool(rec.get("placeholder"))}


PARALLEL_SCENES = 3  # Muse Image allows 150 requests/min; 3 at once keeps a film well inside that


def run(job: Job, script: Script, only: set[int] | None = None) -> None:
    """Paint every scene in parallel (each with its own verify loop); cards keep scene order.
    only: paint just these scene numbers and keep the other cards (Gara-gara paints scenes in two passes)."""
    todo = [sc for sc in script.scenes if only is None or sc.n in only]
    job.stage("scenes", "running", f"Muse Image is painting {len(todo)} scenes at once...", clear_thumbs=only is None)
    meter = cost.current()
    numbers = {sc.n for sc in script.scenes}
    done: dict[int, dict] = {} if only is None else {c["n"]: c for c in job.s.get("scenes", [])
                                                     if c["n"] in numbers and c["n"] not in only}

    def work(scene: Scene) -> dict:
        cost.use(meter)  # the budget meter is per thread; share the job's meter with the workers
        try:
            return paint_one(job, script, scene)
        finally:
            cost.use(None)

    with ThreadPoolExecutor(max_workers=PARALLEL_SCENES) as pool:
        futures = {pool.submit(work, sc): sc.n for sc in todo}
        for fut in as_completed(futures):
            card = fut.result()
            done[card["n"]] = card
            job.set(scenes=[done[n] for n in sorted(done)])
            job.stage("scenes", detail=f"{len(done)} of {len(script.scenes) if only is None else len(done)} scenes painted and checked",
                      thumb=card["still"])
    cards = [done[n] for n in sorted(done)]
    redraws = sum(len(c["rejections"]) for c in cards)
    extra = f" \u00b7 checker asked for {redraws} redraw{'s' if redraws != 1 else ''}" if redraws else ""
    job.stage("scenes", "done", f"{len(cards)} scenes painted and checked{extra}")


def redo(job: Job, n: int, narration: str | None, repaint: bool) -> None:
    """Storyboard review: edit one narration line and/or repaint one scene."""
    script = Script(**job.s["script"])
    scene = next(s for s in script.scenes if s.n == n)
    if narration is not None and narration.strip():
        scene.narration = narration.strip()[:300]
    cards = job.s["scenes"]
    idx = next(i for i, c in enumerate(cards) if c["n"] == n)
    if repaint:
        job.stage("scenes", "running", f"Repainting scene {n}...")
        bg = job.dir / f"bg_{n}.png"
        # A fresh variation each time: the nudge keeps the prompt cache from returning the same picture.
        cards[idx]["redos"] = cards[idx].get("redos", 0) + 1
        nudge = f" Variation {cards[idx]['redos'] + 1}: a different composition."
        verify.make_verified(job, "scenes", f"scene {n}",
                             prompts.backdrop_prompt(scene.image_prompt, scene.mood, job.s["style"]) + nudge,
                             bg, must_show=f"an EMPTY wayang-style backdrop: {scene.setting}", context=scene.action)
        job.stage("scenes", "done")
    still = storyboard_still(job, script, scene, job.dir / f"still_{n}.jpg")
    cards[idx].update({"narration": scene.narration, "still": job.url(still), "backdrop": job.url(job.dir / f"bg_{n}.png")})
    job.set(script=script.model_dump(), scenes=cards)
