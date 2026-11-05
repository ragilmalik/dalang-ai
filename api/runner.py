"""Runs the 9-stage pipeline for a job in a background thread."""
from __future__ import annotations

import json
import logging
import shutil
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from . import cost, db, errors, logs, storage
from .config import settings
from .jobs import Job
from .pipeline import animate, casting, consistency, cut, director, gamelan, garagara, lakon, listen, narrate, penjaga, scenes
from .schemas import Script

log = logging.getLogger("dalang.runner")
pool = ThreadPoolExecutor(max_workers=2)
DEMO_DIR = settings.data_dir / "demo"


def _meter(job: Job) -> cost.Meter:
    m = cost.Meter(settings.job_budget_usd)
    m.spent = float(job.s.get("cost_usd", 0.0))
    m.items = dict(job.s.get("cost_items") or {})
    m.trace = list(job.s.get("trace") or [])
    m.tokens = {k: list(v) for k, v in (job.s.get("tokens") or {}).items()}
    m.stage_of = lambda: next((s["key"] for s in job.s["stages"] if s["status"] == "running"), None)

    def live(trace: list) -> None:  # the trace rides along with the next state save (stage updates, SSE)
        with job.lock:
            job.s["trace"] = trace

    m.listener = live
    cost.use(m)
    return m


def _guarded(fn):
    def wrapper(job: Job, *a, **kw):
        meter = _meter(job)
        token = logs.job_id.set(job.id)  # every log line from this film's thread carries its id
        log.info("job %s: %s started (mode %s)", job.id, fn.__name__.lstrip("_"), settings.mode)
        try:
            fn(job, *a, **kw)
        except listen.Blocked as b:
            job.set(status="blocked", message=str(b))
        except Exception as e:  # noqa: BLE001
            # The full story (traceback, file paths) stays in the server log; the family sees a kind message.
            kind, public = errors.public(e)
            log.error("Job %s failed (%s): %s", job.id, kind, traceback.format_exc())
            running = next((s for s in job.s["stages"] if s["status"] == "running"), None)
            if running:
                job.stage(running["key"], "failed", public)
            if not replay_demo(job, public):
                job.set(status="failed", error=public, error_kind=kind,
                        **({"message": UNREACHABLE} if kind == "meta" else {}))
        finally:
            if job.s["status"] in {"failed", "blocked", "done"}:
                forget_recording(job)
            log.info("job %s: %s ended, status %s, $%.4f", job.id, fn.__name__.lstrip("_"), job.s["status"],
                     meter.spent)
            logs.job_id.reset(token)
            job.set(cost_usd=round(meter.spent, 4), cost_items={k: round(v, 5) for k, v in meter.items.items()},
                    trace=meter.trace, trace_summary=cost.summary(meter.trace, meter.items),
                    tokens=meter.tokens)
            job.set(receipt=cost.receipt(job.s))
            cost.use(None)
    return wrapper


@_guarded
def _front(job: Job, audio: Path | None, text: str | None) -> None:
    job.set(status="running")
    transcript = listen.run(job, audio, text)
    script = lakon.polish(job, lakon.run(job, transcript))
    script = penjaga.run(job, script)  # cultural review: fixes go into the script before anything is drawn
    job.set(voice_scene_total=len(script.scenes))
    casting.run(job, script)
    if (job.s.get("gara_gara") or {}).get("enabled"):
        kept = garagara.split_point(script)
        scenes.run(job, script, only=set(range(1, kept + 1)))
        garagara.pause(job, script, kept)  # status "choice": the film waits for the child's answer
        return
    scenes.run(job, script)
    _review_or_render(job)


def _review_or_render(job: Job) -> None:
    if job.s["review"]:
        job.set(status="review")
    else:
        _back_inner(job)


def _back_inner(job: Job) -> None:
    job.set(status="rendering")
    script = Script(**job.s["script"])
    fresh = job.s.get("fresh_scenes")
    only = set(fresh) if fresh is not None else None  # after a gara-gara choice, re-render only the new scenes
    director.plan(job, script)  # Muse Spark directs camera, entrances/exits, transitions, gamelan cues and sfx
    job.set(score=gamelan.summary([sc.mood for sc in script.scenes]))
    plans = animate.run(job, script, only)
    voices = narrate.run(job, script, only)
    vids = cut.run(job, script, plans, voices)
    consistency.record(job, script, "in the final film")
    forget_recording(job)  # privacy: the child's own recording is deleted as soon as the film is made
    urls = {k: storage.publish(job, v) for k, v in vids.items()}
    poster = job.dir / "poster.jpg"
    job.set(status="done", videos=urls, poster=job.url(poster) if poster.exists() else None)


@_guarded
def _back(job: Job) -> None:
    _back_inner(job)


@_guarded
def _choice(job: Job, audio: Path | None, text: str | None) -> None:
    job.set(status="running", message=None)
    try:
        garagara.apply_choice(job, audio, text)
    except listen.Blocked as b:  # an unsuitable or unheard answer: ask again instead of ending the film
        gara = {**job.s["gara_gara"], "status": "waiting", "answer": None}
        job.stage("lakon", "done")
        job.set(status="choice", gara_gara=gara, message=str(b))
        return
    _review_or_render(job)


@_guarded
def _redo(job: Job, n: int, narration: str | None, repaint: bool) -> None:
    job.set(status="running")
    scenes.redo(job, n, narration, repaint)
    if job.s.get("fresh_scenes") is not None and n not in job.s["fresh_scenes"]:
        job.set(fresh_scenes=sorted({*job.s["fresh_scenes"], n}))
    job.set(status="review")


def forget_recording(job: Job) -> None:
    """Delete the kept story recording (only kept for "child" narration) and its timestamps."""
    (job.dir / "story.wav").unlink(missing_ok=True)
    if job.s.get("voice_turns"):
        job.set(voice_turns=[{k: v for k, v in t.items() if k != "text"} for t in job.s["voice_turns"]])


# Suffixes an uploaded recording is stored under (api/main.py maps anything else to .webm).
AUDIO_SUFFIXES = (".webm", ".m4a", ".mp3", ".wav", ".ogg", ".oga", ".opus", ".aac", ".mp4", ".3gp", ".amr", ".flac")
RECORDING_NAMES = ("story.wav", *(f"upload{s}" for s in AUDIO_SUFFIXES), *(f"answer_upload{s}" for s in AUDIO_SUFFIXES))


def sweep_recordings(hours: float | None = None) -> list[str]:
    """Privacy sweep: delete a recording left behind by a film nobody approved or finished (a storyboard that
    sat in review, or a crash). Any story.wav / upload.* file older than `hours` (RECORDING_TTL_HOURS, default 6)
    goes, except for films this process is still working on. Returns the ids that were cleaned. hours <= 0 = off."""
    import time

    hours = settings.recording_ttl_hours if hours is None else hours
    if hours <= 0:
        return []
    jobs_dir = settings.data_dir / "jobs"
    if not jobs_dir.is_dir():
        return []
    cutoff = time.time() - hours * 3600
    mine = active_ids()
    cleaned = []
    for d in jobs_dir.iterdir():
        if not d.is_dir() or d.name in mine:
            continue
        old = [f for f in d.iterdir() if f.name in RECORDING_NAMES and f.is_file() and f.stat().st_mtime < cutoff]
        if not old:
            continue
        for f in old:
            f.unlink(missing_ok=True)
        job = Job.get(d.name)
        if job:
            forget_recording(job)
        cleaned.append(d.name)
    if cleaned:
        log.info("recording sweep: removed leftover recordings of %d film(s)", len(cleaned))
    return cleaned


_futures: dict[str, Future] = {}  # job id -> its latest piece of work in the pool


def _submit(job: Job, fn, *args) -> None:
    _futures[job.id] = pool.submit(fn, job, *args)


def active_ids() -> set[str]:
    """Jobs this process is working on (queued in the pool or running)."""
    return {jid for jid, f in list(_futures.items()) if not f.done()}


def start(job: Job, audio: Path | None, text: str | None) -> None:
    _submit(job, _front, audio, text)


def approve(job: Job) -> None:
    _submit(job, _back)


def choice(job: Job, audio: Path | None, text: str | None) -> None:
    _submit(job, _choice, audio, text)


def redo(job: Job, n: int, narration: str | None, repaint: bool) -> None:
    _submit(job, _redo, n, narration, repaint)


@_guarded
def _remix(job: Job) -> None:
    from .pipeline import remix as remix_pipeline

    remix_pipeline.run(job)


def remix(job: Job) -> None:
    _submit(job, _remix)


UNREACHABLE = errors.MESSAGES["meta"]
INTERRUPTED = ("Server dimulai ulang saat filmmu dibuat. Coba lagi, ya! \u00b7 "
               "The server restarted while your film was being made. Please try again.")


def _interrupt(job: Job) -> None:
    for st in job.s["stages"]:
        if st["status"] == "running":
            job.stage(st["key"], "failed", "interrupted by a server restart")
    job.set(status="failed", error=INTERRUPTED, error_kind="restart", message=INTERRUPTED)


def recover() -> list[str]:
    """On startup: jobs a restart cut short (queued, running or rendering, but not in this process's pool) become
    'failed' with a kind try-again message, instead of spinning forever. Films waiting for the family (review,
    gara-gara choice) are untouched: their state is complete and the next click resumes them."""
    mine = active_ids()
    done = []
    for state in db.with_status(["queued", "running", "rendering"]):
        job = Job.get(state["id"])
        if job and job.id not in mine:
            _interrupt(job)
            done.append(job.id)
    if done:
        log.warning("recovered %d interrupted job(s): %s", len(done), ", ".join(done))
    return done


def shutdown() -> list[str]:
    """On shutdown: cancel work that has not started yet and tell those families; running stages finish (the
    interpreter waits for pool threads), and anything cut off by a hard kill is caught by recover() next start."""
    cancelled = []
    for jid, fut in list(_futures.items()):
        if fut.cancel():
            job = Job.get(jid)
            if job:
                _interrupt(job)
            cancelled.append(jid)
    return cancelled


def cleanup(days: float) -> list[str]:
    """Delete private films (never shared, not samples) untouched for `days` days: files and database row.
    Shared films and samples are kept. days <= 0 turns cleanup off."""
    if days <= 0:
        return []
    import time

    removed = []
    mine = active_ids()
    for state in db.older_than(time.time() - days * 86400):
        if state.get("public") or state.get("sample") or state["id"] in mine:
            continue
        shutil.rmtree(settings.data_dir / "jobs" / state["id"], ignore_errors=True)
        db.delete(state["id"])
        Job.forget(state["id"])
        removed.append(state["id"])
    if removed:
        log.info("cleanup: removed %d private film(s) older than %s days", len(removed), days)
    return removed


def replay_demo(job: Job, reason: str) -> bool:
    """DEMO_MODE (spec §8): if a live run fails on stage, play the pre-generated film instead."""
    if not settings.demo_mode or not (DEMO_DIR / "dalang_landscape.mp4").exists():
        return False
    urls = {}
    for name in ("landscape", "vertical"):
        src = DEMO_DIR / f"dalang_{name}.mp4"
        if src.exists():
            shutil.copyfile(src, job.dir / src.name)
            urls[name] = job.url(job.dir / src.name)
    if (DEMO_DIR / "poster.jpg").exists():
        shutil.copyfile(DEMO_DIR / "poster.jpg", job.dir / "poster.jpg")
    meta = json.loads((DEMO_DIR / "job.json").read_text()) if (DEMO_DIR / "job.json").exists() else {}
    job.set(status="done", videos=urls, poster=job.url(job.dir / "poster.jpg"), demo_replay=True,
            title=meta.get("title", job.s.get("title")), script=job.s.get("script") or meta.get("script"),
            message=f"{reason} \u00b7 Jadi ini film yang dibuat sebelumnya. \u00b7 So this is a film made earlier.")
    return True
