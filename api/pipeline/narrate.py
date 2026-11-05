"""Stage 7 - Narrate. Two voices:

* "tts" (default): Meta Model API has no text-to-speech model (Muse Voice Transcribe is speech-to-text only), so
  the narrator is a text-to-speech voice picked per language in api/tts.py (TTS_ENGINE), with edge-tts as the
  fallback. If no voice is reachable the film keeps its subtitles and plays without narration.
* "child": the child's OWN voice. Muse Voice Transcribe returns speech turns with startMs/endMs; the turns are
  shared out over the scenes in order and each scene's narration is cut from the original recording. The
  recording is kept only until the film is made, then deleted. Without timestamps (Javanese goes through Muse
  Spark audio, which returns text only) or with too few turns, the film falls back to the TTS narrator.
"""
from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..jobs import Job
from ..schemas import Scene, Script
from . import media

PAD_MS = 150


def recording(job: Job) -> Path:
    """Where the child's own recording is kept while the film is made (deleted when it is done)."""
    return job.dir / "story.wav"


def child_groups(turns: list[dict], scenes_total: int) -> list[list[dict]] | None:
    """Share the speech turns out over the scenes in story order, about equal speaking time each.
    None when there are fewer turns than scenes (then every scene would not get the child's words)."""
    if scenes_total <= 0 or len(turns) < scenes_total:
        return None
    turns = sorted(turns, key=lambda t: t["start_ms"])
    total = sum(t["end_ms"] - t["start_ms"] for t in turns)
    groups: list[list[dict]] = [[]]
    acc = 0.0
    for i, t in enumerate(turns):
        to_open = scenes_total - len(groups)
        boundary = total * len(groups) / scenes_total
        if groups[-1] and to_open > 0 and (len(turns) - i <= to_open or acc >= boundary):
            groups.append([])
        groups[-1].append(t)
        acc += t["end_ms"] - t["start_ms"]
    return groups if len(groups) == scenes_total else None


def child_plan(job: Job) -> dict[int, list[dict]]:
    """Scene number -> the child's turns for it. Scenes rewritten after a gara-gara choice are not in the
    original recording, so they are left to the TTS narrator."""
    turns = job.s.get("voice_turns") or []
    if job.s.get("narration_voice") != "child" or not turns or not recording(job).exists():
        return {}
    total = int(job.s.get("voice_scene_total") or len((job.s.get("script") or {}).get("scenes", [])))
    groups = child_groups(turns, total)
    if not groups:
        return {}
    fresh = set(job.s.get("fresh_scenes") or [])
    return {n: g for n, g in enumerate(groups, 1) if n not in fresh}


def cut_child(job: Job, group: list[dict], out_wav: Path) -> Path | None:
    """Cut one scene's stretch of the child's recording (padded, faded, loudness-normalised); None if ffmpeg fails."""
    start = max(0, group[0]["start_ms"] - PAD_MS) / 1000
    end = (group[-1]["end_ms"] + PAD_MS) / 1000
    try:
        media.run(["-ss", f"{start:.3f}", "-t", f"{max(0.3, end - start):.3f}", "-i", str(recording(job)), "-ac", "1",
                   "-ar", str(media.SR), "-c:a", "pcm_s16le", "-af", "afade=t=in:d=0.05,loudnorm=I=-18:TP=-2",
                   str(out_wav)])
        return out_wav
    except RuntimeError:
        return None


def voice_for(job: Job, script: Script, scene: Scene, plan: dict[int, list[dict]] | None = None) -> Path | None:
    """One scene's narration: the child's own words when available, else the TTS narrator."""
    vdir = job.dir / "voice"
    vdir.mkdir(exist_ok=True)
    wav = vdir / f"scene_{scene.n}.wav"
    plan = child_plan(job) if plan is None else plan
    if scene.n in plan:
        got = cut_child(job, plan[scene.n], wav)
        if got:
            lines = dict(job.s.get("child_lines") or {})
            lines[str(scene.n)] = " ".join(t["text"] for t in plan[scene.n] if t["text"])[:300]
            job.set(child_lines=lines)
            (vdir / f"scene_{scene.n}.txt").write_text("child:" + scene.narration, encoding="utf-8")
            return got
    got = media.narrate(scene.narration, script.language, wav) if settings.narration_voice else None
    if got:
        (vdir / f"scene_{scene.n}.txt").write_text(scene.narration, encoding="utf-8")
    return got


def run(job: Job, script: Script, only: set[int] | None = None) -> list[Path | None]:
    """only: speak just these scenes; reuse a saved line when its text is unchanged (Gara-gara re-render)."""
    job.stage("narrate", "running", "Ki Dalang is reading the story aloud...")
    out: list[Path | None] = []
    vdir = job.dir / "voice"
    vdir.mkdir(exist_ok=True)
    plan = child_plan(job)
    opening = bool(script.opening) and not (only is not None and (vdir / "opening.wav").exists())
    if settings.narration_voice:  # a local voice (Kokoro) renders every line in one model load, before any is used
        from .. import tts

        todo = [script.opening] if opening else []
        todo += [sc.narration for sc in script.scenes if sc.n not in plan and (only is None or sc.n in only)]
        tts.prefetch(todo, script.language, vdir)
    if settings.narration_voice and opening:
        media.narrate(script.opening, script.language, vdir / "opening.wav")  # the dalang always opens the show
    for scene in script.scenes:
        wav = vdir / f"scene_{scene.n}.wav"
        said = vdir / f"scene_{scene.n}.txt"
        if (only is not None and scene.n not in only and wav.exists() and said.exists()
                and said.read_text(encoding="utf-8").removeprefix("child:") == scene.narration):
            out.append(wav)
            continue
        out.append(voice_for(job, script, scene, plan))
    spoken = sum(1 for w in out if w)
    voice = media.voice_name(script.language)
    if plan:
        detail = f"{len(plan)} scene(s) in the child's own voice" + (
            f", {spoken - len(plan)} by {voice}" if spoken > len(plan) else "")
    elif job.s.get("narration_voice") == "child":
        detail = f"Child's voice unavailable (no speech timestamps), narrated in {voice}" if spoken else "Subtitles only"
    else:
        detail = f"Narrated in {voice}" if spoken else "Subtitles only (voice service unreachable)"
    job.stage("narrate", "done", detail)
    return out
