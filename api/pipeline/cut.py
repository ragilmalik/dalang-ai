"""Stage 9 - Final cut: title card, every scene re-timed to its narration, gunungan transitions,
subtitles, gamelan-style sound, in 16:9 and 9:16. Encoded with ffmpeg."""
from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .. import qr
from ..config import settings
from ..jobs import Job
from ..schemas import Scene, Script
from . import director, engine, media, scenes


def spoken_line(job: Job, scene: Scene) -> str:
    """Subtitle text: the child's own words for scenes narrated in the child's voice, else the narration."""
    return (job.s.get("child_lines") or {}).get(str(scene.n)) or scene.narration


def title_aksara(job: Job, script: Script) -> str:
    """The title in Javanese script for the title card, kept on the job as `title_aksara`."""
    from .. import aksara

    ak = aksara.transliterate(script.title)
    if job.s.get("title_aksara") != ak:
        job.set(title_aksara=ak)
    return ak


def build_film(job: Job, script: Script, plans: list[dict], voices: list[Path | None], W: int, H: int,
               scene_list: list[Scene] | None = None, end_title: str | None = None, end_sub: str | None = None,
               with_title: bool = True) -> engine.Film:
    """Assemble one film shape (W x H): title card, every scene's shots with its motion plan and narration, captions, gunungan transitions and the end card."""
    g_path = job.dir / "puppets" / "gunungan.png"
    gunungan = None
    if g_path.exists():
        gunungan = Image.open(g_path).convert("RGBA")
        s = (H * 1.02) / gunungan.height
        gunungan = gunungan.resize((max(1, int(gunungan.width * s)), max(1, int(gunungan.height * s))), Image.Resampling.LANCZOS)
    if job.s.get("sample"):  # a sample story written for this project, not a child's own story
        sub_title = {"id": "Dalang AI \u00b7 contoh cerita", "jv": "Dalang AI \u00b7 conto crita",
                     "en": "Dalang AI \u00b7 a sample story"}.get(script.language, "Dalang AI")
    else:
        sub_title = {"id": "Dalang AI \u00b7 cerita dari suara anak", "jv": "Dalang AI \u00b7 crita saka swarane bocah",
                     "en": "Dalang AI \u00b7 a story told by a child"}.get(script.language, "Dalang AI")
    opening_wav = job.dir / "voice" / "opening.wav"
    has_opening = bool(script.opening) and opening_wav.exists()
    title_len = max(3.5, media.wav_seconds(opening_wav) + 1.8) if has_opening else 3.5
    film = engine.Film(
        W, H, style=job.s["style"], gunungan=gunungan, title_len=title_len, end_len=4.0,
        opening_wav=opening_wav if has_opening else None,
        opening_caption=engine.caption_layer(script.opening, W, H) if script.opening else None,
        title_card=engine.card(W, H, script.title, sub_title, gunungan, aksara_line=title_aksara(job, script)),
        end_card=engine.card(W, H, end_title or script.moral or script.title,
                             end_sub or "Made with Dalang AI \u00b7 Meta Muse Image, Muse Spark, Muse Wonder, SAM 3.1",
                             gunungan),
    )
    if end_title is not None:
        film.end_len = 4.5
    if settings.public_base_url and end_title is None:  # only a real deployed link goes into the film itself, never the placeholder
        film.end_qr = engine.qr_badge(qr.image(qr.app_url()), W, H, qr.base_url().split("://", 1)[-1][:28])
    shots = {s["n"]: s for s in (job.s.get("director") or {}).get("shots", [])}
    for scene, plan, voice in zip(scene_list if scene_list is not None else script.scenes, plans, voices, strict=False):
        speech = media.wav_seconds(voice) if voice else len(scene.narration.split()) / 2.3
        cue = shots.get(scene.n)
        film.shots.append(engine.Shot(
            duration=max(scene.duration_s * 0.8, speech + 1.4, 4.5),
            bg=engine.cover(job.dir / f"bg_{scene.n}.png", W, H, 1.12),
            plan=director.apply(plan, cue) if cue else plan, mood=scene.mood,
            caption=engine.caption_layer(spoken_line(job, scene), W, H), narration_wav=voice, cue=cue))
    return film


def _render(job: Job, script: Script, plans: list[dict], voices: list[Path | None], name: str, W: int, H: int,
            progress: Callable[[float], None]) -> Path:
    film = build_film(job, script, plans, voices, W, H)
    kel = engine.Kelir(film, scenes.load_puppets(job, script, engine.ref_size(W, H)))
    silent = job.dir / f"_{name}_silent.mp4"
    engine.encode(kel, silent, settings.fps, progress)
    if name == "landscape":
        engine.poster(kel, script.title, job.dir / "poster.jpg")
    audio = engine.soundtrack(film, job.dir / f"_{name}.wav")
    out = job.dir / f"dalang_{name}.mp4"
    media.run(["-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
               "-shortest", "-movflags", "+faststart", str(out)])
    silent.unlink(missing_ok=True)
    audio.unlink(missing_ok=True)
    if name == "landscape":
        job.set(duration_s=round(film.total, 1))
        vtt = engine.captions_vtt(film, script.opening, [spoken_line(job, s) for s in script.scenes],
                                  job.dir / "captions.vtt")
        job.set(captions=job.url(vtt))
    return out


def run(job: Job, script: Script, plans: list[dict], voices: list[Path | None]) -> dict:
    """Render 16:9 and 9:16 side by side (PIL compositing and x264 release the GIL), roughly halving the wait."""
    job.stage("cut", "running", "Cutting the film...")
    formats = [("landscape", 1280, 720)] + ([("vertical", 720, 1280)] if settings.make_vertical else [])
    done = {name: 0.0 for name, _, _ in formats}
    last = [-1]
    lock = threading.Lock()

    def progress_for(name: str) -> Callable[[float], None]:
        def prog(p: float) -> None:
            with lock:
                done[name] = p
                pct = int(sum(done.values()) / len(done) * 100) // 5 * 5
                if pct == last[0]:
                    return
                last[0] = pct
            job.stage("cut", detail=f"Rendering the film... {pct}%")
        return prog

    with ThreadPoolExecutor(max_workers=max(1, min(len(formats), settings.render_workers))) as pool:
        futs = {name: pool.submit(_render, job, script, plans, voices, name, W, H, progress_for(name))
                for name, W, H in formats}
        videos = {name: f.result() for name, f in futs.items()}
    job.stage("cut", "done", f"{int(job.s.get('duration_s', 0))} second film ready")
    return videos
