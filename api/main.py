"""Dalang AI API (FastAPI). Run: uvicorn api.main:app --port 8000"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import ipaddress
import json
import logging
import re
import threading
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import aksara, cost, db, kotak, logs, printable, qr, resilience, runner, samples, thumbs
from .config import settings
from .jobs import Job

logs.setup()
log = logging.getLogger("dalang.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup: recover films a restart cut short, clean up old private films, maybe seed samples.
    Shutdown: cancel work that has not started (running stages finish)."""
    runner.recover()
    runner.cleanup(settings.cleanup_days)
    runner.sweep_recordings()
    if settings.bundled_samples:
        try:
            samples.import_bundled()
        except Exception:  # noqa: BLE001 - a broken sample must never stop the app
            log.exception("could not add the bundled sample films")
    if settings.seed_samples:
        if settings.fake_meta:
            samples.seed_in_background()
        else:  # real models cost money: samples are only made on purpose (scripts/seed_gallery.py --live)
            log.warning("SEED_SAMPLES ignored: a Meta key is set, run scripts/seed_gallery.py --live on purpose")
    yield
    cancelled = runner.shutdown()
    if cancelled:
        log.warning("shutdown: %d queued film(s) cancelled, families will see a try-again message", len(cancelled))


TAGS = [
    {"name": "films", "description": "Story in, wayang film out: the 7-stage pipeline on six Meta models, its live "
                                     "progress, storyboard review, gara-gara choice and the agent trace."},
    {"name": "community", "description": "Gallery, Sembah votes, share links and QR codes. Films are private until shared."},
    {"name": "kotak wayang", "description": "A family's puppet box: keep a puppet and bring it back in the next story."},
    {"name": "family testing", "description": "In-app feedback (ratings and comments)."},
    {"name": "system", "description": "Health and configuration."},
    {"name": "media", "description": "Static files of a film."},
]
DESCRIPTION = """Tell a story out loud, get back an animated Javanese wayang kulit film.

Pipeline: Muse Voice Transcribe (or Muse Spark 1.2 audio for Basa Jawa) -> Muse Spark (structured lakon script) ->
Muse Image (puppets, backdrops) -> SAM 3.1 (puppet cut-outs reused in every scene) -> Muse Spark vision checker
(verify -> redraw loop) -> Muse Wonder (motion keyframes) -> narration -> ffmpeg final cut in 16:9 and 9:16.

Try it: `POST /api/jobs` with `text` = a short story and `review=false`, then poll `GET /api/jobs/{id}` (or stream
`/events`) until `status` is `done`; `GET /api/jobs/{id}/trace` shows every Meta call behind the film.
With a Meta key every call goes to the live Meta Model API. Without one the gallery's sample films still play but
new films are refused (503). FAKE_META=1 answers every call from the built-in fake API (tests, offline; labelled).
How the models are used: docs/META_MODELS.md."""

app = FastAPI(title="Dalang AI", version="1.0", lifespan=lifespan, description=DESCRIPTION, openapi_tags=TAGS,
              license_info={"name": "MIT"})
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])

MAX_UPLOAD = 25 * 1024 * 1024
MAX_BODY = MAX_UPLOAD + 256 * 1024  # a whole multipart request: the recording plus the form fields
# Suffixes a story recording is stored under (anything else is saved as .webm and left to ffmpeg to read).
AUDIO_SUFFIXES = set(runner.AUDIO_SUFFIXES)
# Raw recordings stay on the server only until they are transcribed; /media never hands them out.
PRIVATE_MEDIA = re.compile(r"(?:^|/)(?:story\.wav|(?:answer_)?upload\.[A-Za-z0-9]+)$|\.(?:json|db|txt)$")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
}


@app.middleware("http")
async def guard(request: Request, call_next):
    """Request id (X-Request-ID, echoed back) on every log line; refuse oversized bodies before they are read; add the
    security headers to every answer; one access-log line per API request (method, path, status, ms; no bodies)."""
    rid = request.headers.get("x-request-id", "")
    rid = rid if logs.RID.fullmatch(rid) else uuid.uuid4().hex[:16]
    token = logs.request_id.set(rid)
    t0 = time.monotonic()
    try:
        response = await _guarded_call(request, call_next)
    except Exception:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse({"detail": "Ada yang salah di server. Coba lagi sebentar lagi. · Something went "
                                           "wrong on the server. Please try again in a moment.", "request_id": rid},
                                status_code=500, headers=SECURITY_HEADERS)
    finally:
        logs.request_id.reset(token)
    response.headers["X-Request-ID"] = rid
    path = request.url.path
    if path.startswith("/api/") and not path.endswith("/events") and path != "/api/health":
        log.info("%s %s %s %.0f ms", request.method, path, response.status_code, (time.monotonic() - t0) * 1000,
                 extra={"request_id": rid, "method": request.method, "path": path,
                        "status": response.status_code, "ms": round((time.monotonic() - t0) * 1000)})
    return response


async def _guarded_call(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            size = int(request.headers.get("content-length") or 0)
        except ValueError:
            size = 0
        if size > MAX_BODY:
            return JSONResponse({"detail": "Rekamannya terlalu besar (maks. 25 MB). \u00b7 "
                                           "Recording too large (max 25 MB, about 90 seconds is plenty)."},
                                status_code=413, headers=SECURITY_HEADERS)
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_via_web() -> JSONResponse:
    """The same spec as /openapi.json, under /api so the website's /api proxy reaches it."""
    return JSONResponse(app.openapi())


@app.get("/api/docs", include_in_schema=False)
def docs_via_web() -> HTMLResponse:
    """The /docs page under /api: the judge page links here, because the website only forwards /api and /media."""
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="Dalang AI · API docs")


def _audio_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in AUDIO_SUFFIXES else ".webm"


async def _read_upload(audio: UploadFile, message: str) -> bytes:
    """Read an upload in chunks and stop as soon as it passes MAX_UPLOAD (a 1 GB file never sits in memory)."""
    if audio.size is not None and audio.size > MAX_UPLOAD:
        raise HTTPException(413, message)
    buf = bytearray()
    while chunk := await audio.read(1024 * 1024):
        buf += chunk
        if len(buf) > MAX_UPLOAD:
            raise HTTPException(413, message)
    return bytes(buf)
ACTIVE = {"queued", "running", "rendering"}
_recent: dict[str, list[float]] = {}  # client ip -> job creation times in the last hour
_recent_lock = threading.Lock()
_bowed: set[str] = set()  # hashes of (film, visitor) that already gave a Sembah


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:  # behind Render / Vercel / the Next.js proxy
        hops = [h.strip() for h in fwd.split(",") if h.strip()]
        n = settings.trusted_proxy_hops
        if hops and n > 0:  # each proxy of ours appends the address it saw: count from the right, ignore typed extras
            return hops[max(len(hops) - n, 0)]
        if hops:
            return hops[0]
    return request.client.host if request.client else "?"


def _from_this_machine(request: Request) -> bool:
    """True only when every hop is this machine: the socket peer and each X-Forwarded-For address.
    A visitor who types "X-Forwarded-For: 127.0.0.1" still arrives from their own address, so they stay limited."""
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    peer = request.client.host if request.client else "?"
    return all(_loopback(h) for h in [*hops, peer])


def _loopback(ip: str) -> bool:
    if ip == "localhost":
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    mapped = getattr(addr, "ipv4_mapped", None)  # "::ffff:127.0.0.1" from the Next.js proxy
    return bool(addr.is_loopback or (mapped and mapped.is_loopback))


def _limit(request: Request) -> None:
    """Abuse guard for a public deployment: a cap on films in progress, and N new films per visitor per hour."""
    if settings.max_active_jobs > 0:
        active = sum(1 for j in list(Job._live.values()) if j.s.get("status") in ACTIVE)
        if active >= settings.max_active_jobs:
            raise HTTPException(429, "Sang dalang sedang sibuk sekali. Coba lagi sebentar lagi, ya! \u00b7 "
                                     "The dalang is very busy right now. Please try again in a minute.")
    ip = _client_ip(request)
    if settings.rate_limit_per_hour <= 0 or _from_this_machine(request):
        return
    now = time.time()
    with _recent_lock:
        times = [t for t in _recent.get(ip, []) if now - t < 3600]
        if len(times) >= settings.rate_limit_per_hour:
            _recent[ip] = times
            raise HTTPException(429, f"Sudah {len(times)} film dalam satu jam. Istirahat dulu, ya! \u00b7 "
                                     f"That's {len(times)} films this hour. Take a break and come back later.")
        _recent[ip] = [*times, now]
        if len(_recent) > 5000:  # keep the table small under a flood of distinct addresses
            for k in [k for k, v in _recent.items() if not v or now - v[-1] >= 3600]:
                del _recent[k]
PUBLIC_FIELDS = ("id", "status", "title", "language", "style", "videos", "poster", "duration_s", "public",
                 "created", "demo_replay", "applause", "captions", "sample", "offline")


NOT_CONFIGURED = ("Server ini belum punya kunci Meta Model API, jadi belum bisa membuat film baru. Contoh film di galeri "
                  "tetap bisa ditonton. · This server has no Meta Model API key yet, so it can't make new films. "
                  "The sample films in the gallery still play.")


def _need_models() -> None:
    """New model work needs the live API (a key) or the explicit fake API (FAKE_META=1, tests and offline)."""
    if settings.mode == "not_configured":
        raise HTTPException(503, NOT_CONFIGURED)


_reach: dict[str, object] = {"t": 0.0, "result": None}


def _models_reachable() -> dict:
    """GET /v1/models on the real API (cached 60 s): reachable, and which of our models it lists."""
    from . import meta_client

    now = time.time()
    if _reach["result"] is not None and now - float(_reach["t"]) < 60:  # type: ignore[arg-type]
        return _reach["result"]  # type: ignore[return-value]
    need = sorted({settings.asr_model, settings.lakon_model, settings.audio_model, settings.image_model,
                   settings.sam_model, settings.animate_model, settings.verify_model})
    t0 = time.monotonic()
    try:
        r = meta_client.client().get(f"{settings.meta_api_base}/models", headers=meta_client._headers(json_body=False),
                                     timeout=10)
        ids = {m.get("id") for m in (r.json().get("data") or [])} if r.status_code == 200 else set()
        result = {"reachable": r.status_code == 200, "status": r.status_code,
                  "missing": [m for m in need if m not in ids] if r.status_code == 200 else need}
    except Exception as e:  # noqa: BLE001
        result = {"reachable": False, "status": None, "error": type(e).__name__, "missing": need}
    result["ms"] = round((time.monotonic() - t0) * 1000)
    _reach.update(t=now, result=result)
    return result


@app.get("/api/ready", tags=["system"], summary="Readiness: storage, ffmpeg and (live mode) Meta API reachability")
def ready() -> JSONResponse:
    """200 when this server can make films right now, else 503 with the reasons. Live mode also checks that
    api.meta.ai answers and lists every model the pipeline uses (cached for 60 s). No key is ever returned."""
    from .pipeline import media

    checks: dict[str, object] = {"mode": settings.mode}
    try:
        db.load("readiness-probe")
        checks["database"] = True
    except Exception:  # noqa: BLE001
        checks["database"] = False
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.data_dir / ".ready"
        probe.write_text("ok")
        probe.unlink()
        checks["storage"] = True
    except OSError:
        checks["storage"] = False
    try:
        checks["ffmpeg"] = bool(media.ffmpeg_exe())
    except RuntimeError:
        checks["ffmpeg"] = False
    ok = all(checks[k] for k in ("database", "storage", "ffmpeg")) and settings.mode != "not_configured"
    if settings.mode == "live":
        meta = _models_reachable()
        checks["meta_api"] = meta
        ok = ok and bool(meta["reachable"]) and not meta["missing"]
    checks["ready"] = ok
    return JSONResponse(checks, status_code=200 if ok else 503)


@app.get("/api/health", tags=["system"], summary="Health, mode and the Meta models in use")
def health() -> dict:
    """Liveness plus configuration. mode: live (real Meta Model API), fake (FAKE_META=1: tests/offline, labelled
    placeholder art) or not_configured (no key: the gallery works, new films are refused with a clear message)."""
    return {
        "ok": True, "mode": settings.mode, "live": settings.live, "offline": settings.fake_meta,
        "fake_meta": settings.fake_meta, "open_weights": settings.open_weights_active,
        "demo_mode": settings.demo_mode,
        "models": {"listen": settings.asr_model, "listen_javanese": settings.audio_model,
                   "lakon": settings.open_model if settings.open_weights_active else settings.lakon_model,
                   "casting_and_scenes": settings.image_model, "cutout": settings.sam_model,
                   "animate": settings.animate_model, "verify": settings.verify_model,
                   "safety": settings.glimmer_model if settings.glimmer_active else settings.lakon_model,
                   **({"polish": settings.glimmer_model} if settings.glimmer_active else {})},
        "open_weights_models": [m for m, on in ((settings.open_model, settings.open_weights_active),
                                                (settings.glimmer_model, settings.glimmer_active)) if on],
        "fonts": {"javanese": aksara.has_font()},
        "resilience": {"breakers": resilience.breaker_states(), "replay": bool(settings.meta_replay_dir),
                       "spend": {"total_usd": round(resilience.ledger.total(), 4), "max_usd_total": resilience.ledger.cap,
                                 "max_usd_per_film": settings.job_budget_usd}},
    }


@app.post("/api/jobs", tags=["films"], summary="Make a film from a recording or typed story")
async def create_job(
    request: Request,
    audio: UploadFile | None = File(None, description="The story recording (webm, m4a, mp3, wav; max 25 MB)."),
    text: str | None = Form(None, description="Or the story typed out (max 2,000 characters).",
                            examples=["Dulu ada kancil yang pintar. Dia mau makan mentimun di seberang sungai..."]),
    language: str = Form("id", description="Story language: id (Bahasa Indonesia), jv (Basa Jawa) or en.", examples=["id"]),
    style: str = Form("classic", description="classic or colorful wayang kulit.", examples=["classic"]),
    review: bool = Form(True, description="Stop at the storyboard for the family to check (false = straight to the film)."),
    gara_gara: bool = Form(False, description="Pause halfway and let the child choose what happens next."),
    narration_voice: str = Form("tts", description="tts, or child: the child's own recording narrates the scenes."),
    family_id: str | None = Form(None, description="Kotak Wayang family id (needed with returning)."),
    returning: str | None = Form(None, description="Comma-separated saved puppet ids to bring back into this story."),
) -> dict:
    """Starts the pipeline in the background and returns the new film's state at once (status `queued`).
    Follow it with `GET /api/jobs/{id}` or `/events`. Answers 413 for oversized input and 429 when the
    per-visitor hourly limit or the films-in-progress cap is reached (both bilingual, kind messages)."""
    _need_models()
    if language not in {"id", "jv", "en"}:
        raise HTTPException(400, "Pilih bahasa cerita: id, jv atau en. \u00b7 language must be id, jv or en")
    if style not in {"classic", "colorful"}:
        style = "classic"
    if audio is None and not (text and text.strip()):
        raise HTTPException(400, "Rekam atau ketik ceritanya dulu, ya! \u00b7 Send a recording or type the story.")
    if narration_voice not in {"tts", "child"}:
        raise HTTPException(400, "narration_voice must be tts or child")
    if text and len(text) > settings.max_story_chars:
        raise HTTPException(413, f"Ceritanya terlalu panjang (maks. {settings.max_story_chars} huruf). \u00b7 "
                                 f"The story is too long (max {settings.max_story_chars} characters).")
    data = b""
    if audio is not None:  # read and check the upload before anything is created
        data = await _read_upload(audio, "Rekamannya terlalu besar (maks. 25 MB). \u00b7 "
                                         "Recording too large (max 25 MB, about 90 seconds is plenty).")
    _limit(request)
    runner.sweep_recordings()  # cheap: old leftover recordings of abandoned films go first
    back = []
    if returning:
        if not kotak.valid_family(family_id):
            raise HTTPException(400, "family_id is needed to bring puppets back from the Kotak Wayang")
        back = kotak.resolve(str(family_id), [x.strip() for x in returning.split(",") if x.strip()])
    job = Job.create(language, style, review, gara_gara=gara_gara, narration_voice=narration_voice, returning=back)
    audio_path = None
    if audio is not None:
        if data:
            audio_path = job.dir / f"upload{_audio_suffix(audio.filename)}"
            audio_path.write_bytes(data)
    runner.start(job, audio_path, text)
    return job.s


JOB_ID = re.compile(r"[A-Za-z0-9]{4,32}")


def _job(jid: str) -> Job:
    job = Job.get(jid) if JOB_ID.fullmatch(jid) else None
    if not job:
        raise HTTPException(404, "Film not found")
    return job


@app.get("/api/jobs/{jid}", tags=["films"], summary="A film's full state (stages, storyboard, videos)")
def get_job(jid: str) -> dict:
    return _job(jid).s


@app.get("/api/jobs/{jid}/trace", tags=["films"], summary="Agent trace: every Meta call and agent decision")
def job_trace(jid: str) -> dict:
    """The film's agent trace: every Meta model call (model, purpose, endpoint, latency, attempts) and every
    agent decision (checker rejections and redraws, validation retries, cache hits, fallbacks), plus totals."""
    s = _job(jid).s
    return {"id": s["id"], "status": s["status"], "summary": s.get("trace_summary") or {}, "cost_usd": s["cost_usd"],
            "receipt": cost.receipt(s), "cultural_review": s.get("cultural_review"),
            "consistency": s.get("consistency"), "trace": s.get("trace") or []}


@app.get("/api/jobs/{jid}/receipt", tags=["films"], summary="Meta models used: calls, tokens, cost estimate")
def job_receipt(jid: str) -> dict:
    """The film's models receipt: every Meta model it used, what for, calls, tokens, images and estimated cost
    (from Meta's published prices), plus the Penjaga Budaya cultural review and the character-consistency score."""
    s = _job(jid).s
    return {"id": s["id"], **cost.receipt(s), "cultural_review": s.get("cultural_review"),
            "consistency": s.get("consistency")}


@app.get("/api/jobs/{jid}/director", tags=["films"], summary="Dalang Director: the shot plan (camera, entrances, "
                                                              "transitions, gamelan cues, sound effects)")
def job_director(jid: str) -> dict:
    d = _job(jid).s.get("director")
    if not d:
        raise HTTPException(404, "This film has no Director plan yet (it is made when the film is rendered).")
    return d


@app.get("/api/gamelan/{mood}.wav", tags=["media"], summary="Procedural gamelan preview for a mood (WAV)")
def gamelan_preview(mood: str, scale: str | None = None, seconds: float = 8.0) -> Response:
    from .pipeline import gamelan

    if mood not in gamelan.MOODS:
        raise HTTPException(400, f"Unknown mood. Choose one of: {', '.join(gamelan.MOOD_NAMES)}.")
    if scale not in (None, "slendro", "pelog"):
        raise HTTPException(400, "scale must be slendro or pelog")
    secs = float(round(min(20.0, max(2.0, seconds))))  # whole seconds, so the cache below stays small
    return Response(_gamelan_wav(mood, secs, scale), media_type="audio/wav",
                    headers={"Cache-Control": "public, max-age=86400"})


@functools.lru_cache(maxsize=48)
def _gamelan_wav(mood: str, secs: float, scale: str | None) -> bytes:
    """The same preview is asked for again and again (each phone on the page); render it once."""
    from .pipeline import gamelan

    return gamelan.wav_bytes(gamelan.render(mood, secs, scale=scale))


@app.get("/api/fonts/NotoSansJavanese.ttf", tags=["media"], summary="Noto Sans Javanese (SIL OFL 1.1) for aksara titles")
def javanese_font() -> FileResponse:
    if not aksara.has_font():
        raise HTTPException(404, "font not bundled")
    return FileResponse(aksara.FONT, media_type="font/ttf", headers={"Cache-Control": "public, max-age=604800"})


@app.get("/api/jobs/{jid}/events", tags=["films"], summary="Live progress (Server-Sent Events)")
async def job_events(jid: str, request: Request) -> StreamingResponse:
    """Server-Sent Events: the full job state every time it changes."""
    job = _job(jid)

    async def stream():
        seen = -1
        last_ping = time.time()
        while True:
            if await request.is_disconnected():
                break
            if job.version != seen:
                seen = job.version
                yield f"data: {json.dumps(job.s)}\n\n"
                if job.s["status"] in {"done", "failed", "blocked", "review", "choice"}:
                    break  # the browser's EventSource reconnects by itself when work resumes
            elif time.time() - last_ping > 15:
                last_ping = time.time()
                yield ": ping\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@app.get("/api/jobs/{jid}/puppets.pdf", tags=["films"], summary="Printable puppets (A4 PDF)")
def puppets_pdf(jid: str) -> FileResponse:
    """Printable puppets (A4): every SAM cut-out large with a dashed cut line, name, cultural note and
    shadow-play instructions in Bahasa Indonesia and English."""
    job = _job(jid)
    if job.s["status"] not in {"review", "choice", "rendering", "done"} or not job.s.get("cast"):
        raise HTTPException(409, "The puppets are not carved yet.")
    out = job.dir / "puppets.pdf"
    printable.build(job.s, job.dir, out)
    name = re.sub(r"[^A-Za-z0-9]+", "-", job.s.get("title") or "dalang").strip("-")[:40] or "dalang"
    return FileResponse(out, media_type="application/pdf", filename=f"{name}-wayang.pdf")


@app.get("/api/jobs/{jid}/storybook.pdf", tags=["films"], summary="Printable storybook (A5 PDF)")
def storybook_pdf(jid: str) -> FileResponse:
    """Storybook (A5): cover with the poster, one page per scene (storyboard picture + narration in big type for
    reading together), then the moral. Available once the storyboard exists."""
    job = _job(jid)
    if job.s["status"] not in {"review", "choice", "rendering", "done"} or not job.s.get("scenes"):
        raise HTTPException(409, "The storyboard is not ready yet.")
    out = job.dir / "storybook.pdf"
    printable.build_storybook(job.s, job.dir, out)
    name = re.sub(r"[^A-Za-z0-9]+", "-", job.s.get("title") or "dalang").strip("-")[:40] or "dalang"
    return FileResponse(out, media_type="application/pdf", filename=f"{name}-storybook.pdf")


@app.post("/api/jobs/{jid}/approve", tags=["films"], summary="Approve the storyboard and render the film")
def approve(jid: str) -> dict:
    _need_models()
    job = _job(jid)
    if job.s["status"] != "review":
        raise HTTPException(409, "This film is not waiting for review.")
    job.set(status="rendering")
    runner.approve(job)
    return job.s


@app.post("/api/jobs/{jid}/choice", tags=["films"], summary="Answer the gara-gara question (text or voice)")
async def gara_choice(jid: str, text: str | None = Form(None), audio: UploadFile | None = File(None)) -> dict:
    """Gara-gara: the child's answer, typed/tapped (text) or spoken (audio). The rest of the lakon is rewritten
    by Muse Spark and only the new scenes are painted, animated and narrated before the final cut."""
    _need_models()
    job = _job(jid)
    if job.s["status"] != "choice":
        raise HTTPException(409, "This film is not waiting for a gara-gara choice.")
    audio_path = None
    if audio is not None:
        data = await _read_upload(audio, "Rekamannya terlalu besar (maks. 25 MB). \u00b7 Recording too large (max 25 MB).")
        if data:
            audio_path = job.dir / f"answer_upload{_audio_suffix(audio.filename)}"
            audio_path.write_bytes(data)
    if audio_path is None and not (text and text.strip()):
        raise HTTPException(400, "Ketuk salah satu pilihan atau rekam jawabanmu. \u00b7 Tap a choice or record your answer.")
    job.set(status="running")
    runner.choice(job, audio_path, text)
    return job.s


class SceneEdit(BaseModel):
    narration: str | None = None
    repaint: bool = False
    model_config = {"json_schema_extra": {"examples": [{"narration": "Kancil melompat dengan riang.", "repaint": False}]}}


# --------------------------------------------------------------------------- vote, remix, stickers
class Vote(BaseModel):
    option: int
    voter: str = ""
    model_config = {"json_schema_extra": {"examples": [{"option": 1, "voter": "device-3f2a"}]}}


def _tally(job: Job) -> dict:
    g = job.s.get("gara_gara") or {}
    v = job.s.get("vote") or {}
    ballots = v.get("ballots") or {}
    tally = [sum(1 for o in ballots.values() if o == i) for i in (0, 1)]
    waiting = job.s["status"] == "choice" and g.get("status") == "waiting"
    status = v.get("status") or ("open" if waiting else "off")
    if status == "open" and not waiting:
        status = "off"
    return {"status": status, "options": g.get("options") or [], "question": g.get("question") or "",
            "tally": tally, "total": sum(tally), "winner": v.get("winner"), "closes_at": v.get("closes_at")}


@app.get("/api/jobs/{jid}/vote", tags=["gara-gara vote"], summary="The live gara-gara vote: question, options, tally")
def vote_get(jid: str) -> dict:
    return _tally(_job(jid))


@app.post("/api/jobs/{jid}/vote", tags=["gara-gara vote"], summary="Cast (or change) one vote for a gara-gara option")
def vote_cast(jid: str, body: Vote, request: Request) -> dict:
    """A family or classroom votes on the gara-gara branch from their phones. One vote per device (`voter`, or the
    caller's address when absent); voting again changes the vote."""
    job = _job(jid)
    if _tally(job)["status"] != "open":
        raise HTTPException(409, "There is no gara-gara vote open for this film right now.")
    if body.option not in (0, 1):
        raise HTTPException(400, "option must be 0 or 1")
    voter = re.sub(r"[^A-Za-z0-9_.:-]", "", body.voter)[:64] or _client_ip(request)
    with job.lock:
        v = dict(job.s.get("vote") or {"status": "open", "ballots": {}, "opened": time.time(), "closes_at": None})
        if len(v["ballots"]) >= 500 and voter not in v["ballots"]:
            raise HTTPException(429, "This vote is full.")
        v["ballots"] = {**v["ballots"], voter: body.option}
        job.s["vote"] = v
    job.save()
    return _tally(job)


@app.post("/api/jobs/{jid}/vote/close", tags=["gara-gara vote"], summary="Close the vote and continue with the winner")
def vote_close(jid: str) -> dict:
    _need_models()
    job = _job(jid)
    t = _tally(job)
    if t["status"] != "open" or t["total"] == 0:
        raise HTTPException(409, "There is no open vote with at least one vote to close.")
    winner = 0 if t["tally"][0] >= t["tally"][1] else 1  # a tie goes to the first option
    answer = t["options"][winner]
    with job.lock:
        job.s["vote"] = {**job.s["vote"], "status": "closed", "winner": winner, "closes_at": time.time()}
        trace = list(job.s.get("trace") or [])
        trace.append({"kind": "decision", "agent": "vote", "t": round(time.time(), 2), "stage": "lakon",
                      "text": f"audience vote {t['tally'][0]}-{t['tally'][1]}: \"{answer}\" wins"})
        job.s["trace"] = trace
    job.set(gara_gara={**job.s["gara_gara"], "status": "answered", "answer": answer}, status="running")
    runner.choice(job, None, answer)
    return {"winner": winner, "answer": answer, "tally": t["tally"]}


class Remix(BaseModel):
    language: str
    pov: str = "original"
    model_config = {"json_schema_extra": {"examples": [{"language": "en", "pov": "villain"}]}}


@app.post("/api/jobs/{jid}/remix", tags=["films"], status_code=202,
          summary="Re-tell a finished film in another language or from the villain's view (same puppets)")
def remix_job(jid: str, body: Remix, request: Request) -> dict:
    from .pipeline import remix as remix_pipeline

    _need_models()
    src = _job(jid)
    if src.s["status"] != "done":
        raise HTTPException(409, "Only a finished film can be remixed.")
    _limit(request)
    try:
        job = remix_pipeline.create(src, body.language, body.pov)
    except remix_pipeline.RemixError as e:
        raise HTTPException(400, str(e)) from e
    runner.remix(job)
    return {"id": job.id, "status": job.s["status"], "remix_of": src.id}


@app.get("/api/jobs/{jid}/stickers", tags=["community"], summary="WhatsApp sticker pack of the film's puppets")
def job_stickers(jid: str) -> dict:
    from . import viral

    job = _job(jid)
    try:
        items = viral.stickers(job)
    except viral.NotReady as e:
        raise HTTPException(409, str(e)) from e
    return {"stickers": items, "zip": f"/api/jobs/{jid}/stickers.zip", "gif": f"/api/jobs/{jid}/loop.gif"}


@app.get("/api/jobs/{jid}/stickers.zip", tags=["community"], summary="The sticker pack as a zip (WebP 512x512 + tray)")
def job_stickers_zip(jid: str) -> FileResponse:
    from . import viral

    job = _job(jid)
    try:
        out = viral.sticker_zip(job)
    except viral.NotReady as e:
        raise HTTPException(409, str(e)) from e
    name = re.sub(r"[^A-Za-z0-9]+", "-", job.s.get("title") or "dalang").strip("-")[:40] or "dalang"
    return FileResponse(out, media_type="application/zip", filename=f"{name}-stickers.zip")


@app.get("/api/jobs/{jid}/loop.gif", tags=["community"], summary="A short looping GIF of the film")
def job_gif(jid: str) -> FileResponse:
    from . import viral

    job = _job(jid)
    try:
        out = viral.gif_loop(job)
    except viral.NotReady as e:
        raise HTTPException(409, str(e)) from e
    return FileResponse(out, media_type="image/gif")


@app.post("/api/jobs/{jid}/scenes/{n}", tags=["films"], summary="Edit a scene's line or redraw it")
def edit_scene(jid: str, n: int, body: SceneEdit) -> dict:
    _need_models()
    job = _job(jid)
    if job.s["status"] != "review":
        raise HTTPException(409, "Scenes can be changed only during storyboard review.")
    if not any(c["n"] == n for c in job.s.get("scenes", [])):
        raise HTTPException(404, "No such scene")
    runner.redo(job, n, body.narration, body.repaint)
    return job.s


class Share(BaseModel):
    public: bool
    model_config = {"json_schema_extra": {"examples": [{"public": True}]}}


@app.post("/api/jobs/{jid}/share", tags=["community"], summary="Share a film to the gallery, or hide it")
def share(jid: str, body: Share) -> dict:
    job = _job(jid)
    if job.s["status"] != "done":
        raise HTTPException(409, "Only finished films can be shared.")
    job.set(public=bool(body.public))
    return job.s


@app.post("/api/jobs/{jid}/applause", tags=["community"], summary="Sembah: one community vote for a public film")
def applause(jid: str, request: Request) -> dict:
    """Community vote: one tap of 'Sembah' (the Javanese bow of thanks) on a public film."""
    job = _job(jid)
    if not (job.s["status"] == "done" and job.s.get("public")):
        raise HTTPException(404, "Film not found")
    # one Sembah per visitor per film (the page remembers it too); kept in memory as a hash, no address is stored
    who = hashlib.sha256(f"{jid}|{_client_ip(request)}".encode()).hexdigest()[:16]
    with _recent_lock:
        repeat = not _from_this_machine(request) and who in _bowed
        if not repeat:
            if len(_bowed) > 50_000:
                _bowed.clear()
            _bowed.add(who)
    if repeat:
        return {"id": jid, "applause": int(job.s.get("applause", 0)), "repeat": True}
    with job.lock:
        job.s["applause"] = int(job.s.get("applause", 0)) + 1
    job.save()
    return {"id": jid, "applause": job.s["applause"]}


@app.get("/api/gallery", tags=["community"], summary="Public films (family films first, then labelled samples)")
def gallery() -> list[dict]:
    """Public finished films, families' own first; labelled sample films after them."""
    films = [{k: j.get(k) for k in PUBLIC_FIELDS} for j in db.gallery()]
    for f in films:  # an 800 px WebP for the grid cards (api/thumbs.py); None means use the full poster
        f["poster_card"] = thumbs.card_url(f.get("poster"))
    return sorted(films, key=lambda f: bool(f.get("sample")))  # stable: newest first within each group


def _request_origin(request: Request) -> str:
    """The address the visitor's browser used (through the website's proxy when there is one)."""
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    if not host or any(ch in host for ch in "/\\@ ") or proto not in {"http", "https"}:
        return str(request.base_url).rstrip("/")
    return f"{proto}://{host}"


@app.get("/api/share-info", tags=["community"], summary="The link QR codes point at")
def share_info(request: Request) -> dict:
    """PUBLIC_BASE_URL once deployed; before that, the address this page was opened on (public=false)."""
    return {"url": qr.base_url(_request_origin(request)), "public": not qr.is_placeholder()}


@app.get("/api/qr.png", tags=["community"], summary="QR code PNG for the app or one page")
def qr_png(request: Request, path: str = "") -> Response:
    """QR code for the app (or one of its pages, e.g. ?path=/watch/abc). Only paths on our own site."""
    if path and (not path.startswith("/") or path.startswith("//") or len(path) > 120):
        raise HTTPException(400, "path must be a page on this site, like /watch/abc123")
    return Response(qr.png_bytes(qr.app_url(path, _request_origin(request))), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=600"})


# ----------------------------------------------------------------------------- family testing
class Feedback(BaseModel):
    job_id: str
    rating: int
    comment: str = ""
    page: str = "film"
    model_config = {"json_schema_extra": {"examples": [{"job_id": "a1b2c3d4", "rating": 5, "comment": "", "page": "film"}]}}


@app.post("/api/feedback", tags=["family testing"], summary="Store a 1-5 smiles rating")
def feedback(body: Feedback) -> dict:
    """1-5 smiles and an optional comment after watching. No names or contact details are asked for or kept."""
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, "rating must be 1 to 5")
    if body.page not in {"film", "watch"}:
        raise HTTPException(400, "page must be film or watch")
    _job(body.job_id)
    fid = db.add_feedback(body.job_id, body.rating, body.comment.strip()[:300], body.page)
    return {"id": fid, "thanks": True}


@app.get("/api/feedback/summary", tags=["family testing"], summary="Ratings summary")
def feedback_summary() -> dict:
    """Counts only (no comments), for the family-testing report in docs/USER_TESTING.md."""
    return db.feedback_summary()


# ----------------------------------------------------------------------------- Kotak Wayang (puppet box)
def _family(fid: str | None) -> str:
    if not kotak.valid_family(fid):
        raise HTTPException(400, "A family id (16-64 letters, digits, - or _) is required.")
    return str(fid)


@app.get("/api/kotak", tags=["kotak wayang"], summary="A family's saved puppets")
def kotak_list(family: str) -> list[dict]:
    return kotak.list_family(_family(family))


class SavePuppet(BaseModel):
    family_id: str
    job_id: str
    char_id: str
    model_config = {"json_schema_extra": {"examples": [{"family_id": "fam_0123456789ab", "job_id": "a1b2c3d4",
                                                        "char_id": "kancil"}]}}


@app.post("/api/kotak", tags=["kotak wayang"], summary="Keep a puppet for the next story")
def kotak_save(body: SavePuppet) -> dict:
    fam = _family(body.family_id)
    job = _job(body.job_id)
    if job.s["status"] not in {"done", "review", "choice"}:
        raise HTTPException(409, "Puppets can be kept once they are carved.")
    try:
        return kotak.save_from_job(fam, job.s, job.dir, body.char_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except OverflowError as e:
        raise HTTPException(409, str(e)) from e


@app.delete("/api/kotak/{pid}", tags=["kotak wayang"], summary="Remove a saved puppet")
def kotak_delete(pid: str, family: str) -> dict:
    if not kotak.delete(_family(family), pid):
        raise HTTPException(404, "No such puppet")
    return {"deleted": pid}


@app.get("/api/kotak/{family}/{name}", tags=["kotak wayang"], summary="A saved puppet's image")
def kotak_image(family: str, name: str) -> FileResponse:
    fam = _family(family)
    if not re.fullmatch(r"[0-9a-f]{12}(_sheet)?\.png", name):
        raise HTTPException(404)
    f = kotak.folder(fam) / name
    if not f.is_file():
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "private, max-age=3600"})


@app.get("/media/{jid}/{path:path}", tags=["media"], summary="A film's files (videos, stills, captions)")
def media(jid: str, path: str) -> FileResponse:
    if not JOB_ID.fullmatch(jid):  # "%2E%2E" would otherwise make the data folder (and its database) the base
        raise HTTPException(404)
    jobs = (settings.data_dir / "jobs").resolve()
    base = (jobs / jid).resolve()
    f = (base / path).resolve()
    if base.parent != jobs or base not in f.parents or not f.is_file() or PRIVATE_MEDIA.search(path):
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "public, max-age=3600"})
