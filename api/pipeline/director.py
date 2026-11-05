"""Dalang Director: Muse Spark plans the film shot by shot as structured JSON, and the kelir engine performs it.

Per scene: a camera move, which puppets enter or exit and from which side, the transition into the next scene
(gunungan sweep / gunungan rise / fade / cut), a gamelan cue and up to three sound effects. One Muse Spark call
(json_schema `director`), validated with Pydantic; unknown puppets and scenes are dropped, missing scenes get a
rule-based shot, and if the call fails the whole plan is rule-based (recorded as a decision either way).

The plan is applied on top of Muse Wonder's keyframe motion (camera and entrances/exits) by `apply()`, and the
cues are rendered by gamelan.py in the soundtrack. The job keeps it as `director` (GET /api/jobs/{id}/director).
"""
from __future__ import annotations

import copy
import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from .. import cost, meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import Script

log = logging.getLogger("dalang.director")

Side = Literal["left", "right", "below"]
Camera = Literal["still", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up"]
Transition = Literal["gunungan_sweep", "gunungan_rise", "fade", "cut"]
Cue = Literal["gong", "kempul", "kendang_rush", "bonang_run", "suwuk", "none"]
Sfx = Literal["keprak", "cempala", "gong", "wind", "water", "birds"]


class Move(BaseModel):
    id: str
    side: Side


class Effect(BaseModel):
    t: float = Field(ge=0.0, le=1.0)
    kind: Sfx

    @field_validator("t", mode="before")
    @classmethod
    def clamp(cls, v: float) -> float:
        return min(1.0, max(0.0, float(v)))


class DirShot(BaseModel):
    n: int
    camera: Camera = "still"
    enter: list[Move] = []
    exit: list[Move] = []
    transition: Transition = "gunungan_sweep"
    gamelan: Cue = "none"
    sfx: list[Effect] = Field(default_factory=list, max_length=3)
    note: str = Field("", max_length=200)

    @field_validator("sfx", mode="before")
    @classmethod
    def at_most_three(cls, v: list) -> list:
        return list(v or [])[:3]

    @field_validator("note", mode="before")
    @classmethod
    def short(cls, v: str) -> str:
        return str(v or "")[:200]


SFX_WORDS = {"water": r"river|sungai|kali|lake|danau|sea|laut|rain|hujan|banyu|segara",
             "wind": r"wind|angin|storm|badai|forest|hutan|alas|mountain|gunung",
             "birds": r"morning|pagi|garden|taman|bird|burung|village|desa|field|sawah"}
MOOD_RULES: dict[str, tuple[Camera, Cue]] = {
    "tense": ("push_in", "kendang_rush"), "happy": ("pan_right", "bonang_run"), "magical": ("pull_out", "kempul"),
    "night": ("still", "kempul"), "triumphant": ("pull_out", "gong"), "calm": ("still", "none"),
}


def rule_shot(script: Script, i: int) -> DirShot:
    """A sensible shot from the scene's mood, cast changes and setting words (used when the model is unavailable)."""
    sc = script.scenes[i]
    camera, cue = MOOD_RULES.get(sc.mood, ("still", "none"))
    prev = set(script.scenes[i - 1].characters) if i else set()
    nxt = set(script.scenes[i + 1].characters) if i + 1 < len(script.scenes) else set(sc.characters)
    facing = {st.id: st.facing for st in sc.staging}
    enter = [Move(id=c, side="left" if facing.get(c, "right") == "right" else "right")
             for c in sc.characters if c not in prev]
    exit_ = [Move(id=c, side="right" if facing.get(c, "right") == "right" else "left")
             for c in sc.characters if c not in nxt] if i + 1 < len(script.scenes) else []
    last = i == len(script.scenes) - 1
    text = f"{sc.setting} {sc.action}".lower()
    sfx = [Effect(t=0.15, kind=k) for k, pat in SFX_WORDS.items() if re.search(pat, text)][:2]  # type: ignore[arg-type]
    if sc.mood == "tense":
        sfx.append(Effect(t=0.5, kind="keprak"))
    if i == 0:
        cue = "gong"
    if last:
        cue = "suwuk"
    return DirShot(n=sc.n, camera=camera, enter=enter, exit=exit_, sfx=sfx[:3], gamelan=cue,
                   transition="fade" if last else ("gunungan_rise" if sc.mood == "magical" else "gunungan_sweep"),
                   note="rule-based: mood " + sc.mood)


def rules(script: Script) -> list[DirShot]:
    return [rule_shot(script, i) for i in range(len(script.scenes))]


def _validate(raw: dict, script: Script) -> tuple[list[DirShot], list[str]]:
    """Model output -> shots, one per scene in order. Returns the shots and what had to be repaired."""
    fixes: list[str] = []
    ids = {c.id for c in script.characters}
    by_n: dict[int, DirShot] = {}
    for item in raw.get("shots") or []:
        try:
            shot = DirShot(**item)
        except (ValidationError, TypeError) as e:
            fixes.append(f"dropped an invalid shot ({str(e).splitlines()[0][:60]})")
            continue
        bad = [m.id for m in shot.enter + shot.exit if m.id not in ids]
        if bad:
            fixes.append(f"scene {shot.n}: removed unknown puppet(s) {', '.join(sorted(set(bad)))}")
            shot.enter = [m for m in shot.enter if m.id in ids]
            shot.exit = [m for m in shot.exit if m.id in ids]
        if any(sc.n == shot.n for sc in script.scenes) and shot.n not in by_n:
            by_n[shot.n] = shot
    out = []
    for i, sc in enumerate(script.scenes):
        if sc.n not in by_n:
            fixes.append(f"scene {sc.n}: no shot planned; used a rule-based shot")
        out.append(by_n.get(sc.n) or rule_shot(script, i))
    if out and out[-1].transition != "fade":
        out[-1].transition = "fade"  # the last scene always settles into the end card
    return out, fixes


def public(shots: list[DirShot], source: str) -> dict:
    """The contract shape (GET /api/jobs/{id}/director)."""
    return {"source": source, "shots": [{
        "n": s.n, "camera": s.camera, "enter": [{"id": m.id, "from": m.side} for m in s.enter],
        "exit": [{"id": m.id, "to": m.side} for m in s.exit], "transition": s.transition, "gamelan": s.gamelan,
        "sfx": [e.model_dump() for e in s.sfx], "note": s.note} for s in shots]}


def plan(job: Job, script: Script) -> dict:
    """Muse Spark directs the film (one structured-output call); falls back to rules. Saved on the job."""
    source = settings.open_model if meta_client.routes_open("director") else settings.lakon_model
    try:
        with cost.labelled("whole film"):
            raw = meta_client.chat_json(
                [{"role": "system", "content": prompts.DIRECTOR_SYSTEM},
                 {"role": "user", "content": prompts.director_user(script.model_dump_json())}],
                prompts.DIRECTOR_SCHEMA, "director", model=settings.lakon_model, reasoning_effort="low",
                purpose="Dalang Director: plan camera, entrances, transitions and gamelan cues")
        job.used(source)
        shots, fixes = _validate(raw, script)
        for f in fixes:
            cost.record_decision(f, agent="director")
    except cost.BudgetExceeded:
        raise
    except Exception as e:  # noqa: BLE001 - a film without the Director still plays: rules direct it
        log.warning("director failed: %s", e)
        shots, source = rules(script), "rule-based fallback"
        cost.record_decision(f"Director unavailable ({str(e)[:70]}); rule-based shots used", agent="director")
    cues = sum(1 for s in shots if s.gamelan != "none")
    moves = sum(len(s.enter) + len(s.exit) for s in shots)
    cost.record_decision(f"planned {len(shots)} shots: {moves} entrances/exits, {cues} gamelan cues, "
                         f"{sum(len(s.sfx) for s in shots)} sound effects", agent="director")
    out = public(shots, source)
    (job.dir / "director.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    job.set(director=out)
    return out


# --------------------------------------------------------------------------- applying the plan
CAMERA = {
    "still": {"zoom_from": 1.02, "zoom_to": 1.02, "pan_x": 0.0, "pan_y": 0.0},
    "push_in": {"zoom_from": 1.0, "zoom_to": 1.14, "pan_x": 0.0, "pan_y": 0.0},
    "pull_out": {"zoom_from": 1.14, "zoom_to": 1.0, "pan_x": 0.0, "pan_y": 0.0},
    "pan_left": {"zoom_from": 1.08, "zoom_to": 1.08, "pan_x": -0.6, "pan_y": 0.0},
    "pan_right": {"zoom_from": 1.08, "zoom_to": 1.08, "pan_x": 0.6, "pan_y": 0.0},
    "tilt_up": {"zoom_from": 1.08, "zoom_to": 1.08, "pan_x": 0.0, "pan_y": -0.5},
}
OFF = {"left": -0.25, "right": 1.25}
ENTER_END, EXIT_START = 0.25, 0.8


def _offstage(side: str, kf: dict) -> dict:
    if side == "below":
        return {**kf, "lift": -0.9}
    return {**kf, "x": OFF[side], "facing": "right" if side == "left" else "left"}


def apply(motion: dict, shot: dict) -> dict:
    """Director shot -> the scene's motion plan: camera move, and entrances/exits as extra keyframes around
    Muse Wonder's own (its keyframes are squeezed into the time the puppet is on stage)."""
    plan = copy.deepcopy(motion)
    plan["camera"] = dict(CAMERA.get(shot.get("camera", ""), plan.get("camera", {})))
    enter = {m["id"]: m["from"] for m in shot.get("enter", [])}
    exit_ = {m["id"]: m["to"] for m in shot.get("exit", [])}
    for tr in plan.get("puppets", []):
        kfs = sorted(tr.get("keyframes") or [], key=lambda k: k["t"])
        if not kfs:
            continue
        a = ENTER_END if tr["id"] in enter else 0.0
        b = EXIT_START if tr["id"] in exit_ else 1.0
        kfs = [{**k, "t": round(a + (b - a) * k["t"], 4)} for k in kfs]
        if tr["id"] in enter:  # off stage at t=0, then glide to Wonder's first mark by ENTER_END
            kfs = [{**_offstage(enter[tr["id"]], kfs[0]), "t": 0.0}] + kfs
        if tr["id"] in exit_:
            last = kfs[-1]
            leave = {**last, "facing": "right" if exit_[tr["id"]] == "right" else "left", "t": b}
            kfs = kfs + [leave, {**_offstage(exit_[tr["id"]], leave), "t": 1.0,
                                 "facing": leave["facing"]}]
        tr["keyframes"] = kfs
    return plan


def apply_all(job: Job, plans: list[dict]) -> list[dict]:
    d = job.s.get("director") or {}
    shots = {s["n"]: s for s in d.get("shots", [])}
    script_ns = [sc["n"] for sc in (job.s.get("script") or {}).get("scenes", [])]
    return [apply(p, shots[n]) if n in shots else p for p, n in zip(plans, script_ns, strict=False)]
