"""meta_client: the ONE module that talks to Meta models (spec §5).

Every endpoint and model id below was checked against Meta's public docs on 2026-10-30:
  * Muse Voice Transcribe  POST /v1/asr/transcribe (multipart)   https://dev.meta.ai/docs/speech-to-text
  * Muse Spark / Wonder    POST /v1/chat/completions             https://dev.meta.ai/docs/structured-output
                           image parts                            https://dev.meta.ai/docs/image-understanding
  * Muse Spark 1.2 audio   input_audio content part               https://dev.meta.ai/docs/video-understanding#audio
  * Muse Image             POST /v1/images/generations, /edits    https://dev.meta.ai/docs/image-generation
  * SAM 3.1                POST /v1/responses (stream=true)       https://dev.meta.ai/docs/media-segmentation
                           output grammar + meta-sam-parser       https://dev.meta.ai/docs/sam/client-libraries
  * Muse Spark Open        Baseten, OpenAI-compatible chat         https://dev.meta.ai/docs/muse-spark-open/deploy#baseten
  * Muse Glimmer           Together AI (or self-hosted), OpenAI-compatible chat
                                                                  https://dev.meta.ai/docs/muse-glimmer/deploy#hosted-providers
Base URL https://api.meta.ai/v1, auth "Authorization: Bearer <key>".
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from . import cost, fileio, resilience
from .config import settings

log = logging.getLogger("dalang.meta")
RETRY_STATUS = {429, 500, 502, 503, 504}


class MetaAPIError(RuntimeError):
    pass


_clients: dict[Any, httpx.Client] = {}


def real_transport() -> httpx.BaseTransport:
    """Network transport for the real API. A transport built by hand ignores HTTPS_PROXY / SSL_CERT_FILE (httpx only
    reads them when it builds its own), so read them here: behind a corporate or sandbox proxy the wrapped clients
    (recording, preflight contract guard) then reach api.meta.ai the same way curl does."""
    import ssl

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or None
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    verify: Any = ssl.create_default_context(cafile=cafile) if cafile and os.path.exists(cafile) else True
    return httpx.HTTPTransport(proxy=proxy, verify=verify)


def client() -> httpx.Client:
    """One pooled HTTP client. Without real keys it is wired to the fake Meta API (api/fake_meta.py).
    META_REPLAY_DIR serves recorded fixtures instead of any network; META_RECORD_DIR records every exchange."""
    if settings.meta_replay_dir:
        key: Any = ("replay", settings.meta_replay_dir)
        if key not in _clients:
            _clients[key] = httpx.Client(transport=resilience.ReplayTransport(Path(settings.meta_replay_dir)), timeout=600)
        return _clients[key]
    fake = settings.fake_meta
    if settings.meta_record_dir:
        key = ("record", fake, settings.meta_record_dir)
        if key not in _clients:
            from . import fake_meta

            inner: httpx.BaseTransport = fake_meta.transport() if fake else real_transport()
            _clients[key] = httpx.Client(transport=resilience.RecordingTransport(inner, Path(settings.meta_record_dir)),
                                         timeout=600)
        return _clients[key]
    if fake not in _clients:
        if fake:
            from . import fake_meta

            _clients[fake] = httpx.Client(transport=fake_meta.transport(), timeout=600)
        else:
            _clients[fake] = httpx.Client(timeout=600)
    return _clients[fake]


def _key(value: str) -> str:
    return value or ("fake-key" if settings.fake_meta else "")


def _headers(json_body: bool = True) -> dict[str, str]:
    h = {"Authorization": f"Bearer {_key(settings.meta_api_key)}"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _endpoint(url: str) -> str:
    path = url.split("://", 1)[-1].split("?", 1)[0]
    return "/" + path.split("/", 1)[1] if "/" in path else path


def _model_of(kw: dict[str, Any]) -> str:
    body = kw.get("json")
    if isinstance(body, dict) and body.get("model"):
        return str(body["model"])
    req = (kw.get("files") or {}).get("request")
    if req:
        try:
            return str(json.loads(req[1]).get("model") or "?")
        except (TypeError, ValueError, IndexError):
            pass
    return "?"


def _post(url: str, *, retries: int | None = None, timeout: float = 300.0, purpose: str = "", **kw: Any) -> httpx.Response:
    """POST with retries on 429/5xx and timeouts (exponential back-off with jitter, Retry-After honoured), behind a
    per-model circuit breaker. Every call is written to the film's agent trace."""
    last: Exception | None = None
    t0 = time.monotonic()
    model, endpoint = _model_of(kw), _endpoint(url)
    attempts = 0
    brk = resilience.breaker(model)
    retries = int(os.environ.get("META_RETRIES", "3")) if retries is None else retries

    def done(ok: bool, error: str = "") -> None:
        cost.record_call(model, endpoint, purpose or endpoint, (time.monotonic() - t0) * 1000, attempts, ok, error)

    if not brk.allow():
        done(False, "circuit open")
        raise MetaAPIError(f"circuit open for {model}: it failed repeatedly, so calls pause for a minute")
    for attempt in range(retries + 1):
        attempts = attempt + 1
        try:
            r = client().post(url, timeout=timeout, **kw)
            if r.status_code in RETRY_STATUS and attempt < retries:
                wait = resilience.backoff(attempt, r.headers.get("retry-after"))
                log.warning("HTTP %s from %s, retry in %ss", r.status_code, url, wait)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                done(False, f"HTTP {r.status_code}")
                if r.status_code in RETRY_STATUS:
                    brk.failure()
                raise MetaAPIError(f"{r.status_code} from {url}: {r.text[:600]}")
            done(True)
            brk.success()
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            if attempt < retries:
                time.sleep(resilience.backoff(attempt))
    done(False, type(last).__name__ if last else "failed")
    brk.failure()
    raise MetaAPIError(f"Request to {url} failed: {last}")


def data_url(path: Path) -> str:
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return f"data:{mime.get(path.suffix.lower(), 'image/png')};base64,{base64.b64encode(path.read_bytes()).decode()}"


def image_part(path: Path, max_side: int = 768) -> dict[str, Any]:
    """Chat Completions image part (an image_url OBJECT on chat completions), downsized to save tokens."""
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    im.thumbnail((max_side, max_side))
    bg = Image.new("RGB", im.size, (128, 128, 128))
    bg.paste(im, mask=im.split()[-1])
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=85)
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}


# --------------------------------------------------------------------------- 1. Listen
def transcribe(wav_path: Path, seconds: float, language_bias: list[str] | None = None,
               keywords: list[str] | None = None) -> str:
    """Muse Voice Transcribe file endpoint. WAV must be mono 16-bit PCM, 16 or 24 kHz, <= 10 min."""
    return transcribe_turns(wav_path, seconds, language_bias, keywords)[0]


def transcribe_turns(wav_path: Path, seconds: float, language_bias: list[str] | None = None,
                     keywords: list[str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Transcript plus speech turns. In ENDPOINTING mode the JSON response carries
    turns[] = {turnId, startMs, endMs, transcript} (turn-level timestamps; there are no word-level ones),
    per https://dev.meta.ai/docs/speech-to-text#transcribe-response. Used to cut the child's own voice per scene."""
    req: dict[str, Any] = {"mode": "ENDPOINTING", "model": settings.asr_model, "audioEncoding": "WAV"}
    if language_bias:
        req["languageBias"] = language_bias
    if keywords:
        req["keywords"] = keywords
    with open(wav_path, "rb") as f:
        r = _post(
            f"{settings.meta_api_base}/asr/transcribe?sessionId=dalang-{uuid.uuid4().hex[:12]}",
            headers=_headers(json_body=False),
            files={"request": (None, json.dumps(req), "application/json"), "audio": (wav_path.name, f, "audio/wav")},
            purpose="transcribe the story (speech turns with timestamps)",
        )
    cost.charge(settings.asr_model, seconds / 3600 * cost.ASR_USD_PER_HOUR)
    j = r.json()
    turns = []
    for t in j.get("turns") or []:
        try:
            start, end = int(t["startMs"]), int(t["endMs"])
        except (KeyError, TypeError, ValueError):
            continue
        if end > start:
            turns.append({"start_ms": start, "end_ms": end, "text": str(t.get("transcript") or "").strip()})
    return (j.get("transcript") or "").strip(), turns


def transcribe_with_spark_audio(wav_path: Path, language_name: str) -> str:
    """Javanese is not among Muse Voice Transcribe's 25 languages, so Javanese stories go through
    Muse Spark 1.2 audio understanding (docs recommend 1.2 for audio; give >= 4000 output tokens)."""
    body = {
        "model": settings.audio_model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"Transcribe this audio. A child or parent is telling a story, mostly in {language_name}. "
                                     "Keep the original language and words. Return only the transcript."},
            {"type": "input_audio", "input_audio": {"data": base64.b64encode(wav_path.read_bytes()).decode(), "format": "wav"}},
        ]}],
    }
    r = _post(f"{settings.meta_api_base}/chat/completions", headers=_headers(), json=body,
              purpose="transcribe Javanese audio (audio understanding)")
    j = r.json()
    cost.charge_tokens(settings.audio_model, j.get("usage"))
    return (j["choices"][0]["message"].get("content") or "").strip()


# --------------------------------------------------------------------------- 2. Text models, structured output
def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text.strip("`")
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    start = min(starts) if starts else 0
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start: end + 1])


OPEN_STAGES = {"lakon", "director", "remix", "cultural_review", "gara_gara", "gara_gara_rewrite"}  # text-only
def routes_open(schema_name: str) -> bool:
    """True when OPEN_WEIGHTS_STAGES sends this structured-output stage to Muse Spark Open (Baseten)."""
    return schema_name in OPEN_STAGES and schema_name in settings.open_stages and settings.open_weights_active


CHAT_RESERVE_USD = 0.005  # headroom checked before a chat call (its real price is known only from `usage` afterwards)

PURPOSES = {  # what each structured-output call is for, as shown in the film's agent trace
    "moderation": "safety screen of the story",
    "lakon": "write the lakon (json_schema script)",
    "polish": "polish title and moral",
    "verdict": "vision check against the script",
    "cultural_review": "Penjaga Budaya: check the lakon against the cultural rules",
    "motion_plan": "choreograph the scene as keyframes",
    "gara_gara": "write the gara-gara question",
    "gara_gara_rewrite": "rewrite the rest of the lakon from the child's answer",
    "director": "Dalang Director: plan camera, entrances, transitions and gamelan cues",
    "remix": "Remix: re-tell the film in new words",
}


def chat_json(messages: list[dict[str, Any]], schema: dict[str, Any], schema_name: str, *,
              model: str | None = None, reasoning_effort: str = "medium", open_weights: bool = False,
              glimmer: bool = False, purpose: str = "") -> Any:
    """Chat Completions with response_format json_schema. Returns the parsed JSON object.
    open_weights: Muse Spark Open on Baseten. glimmer: Muse Glimmer (Together AI or a self-hosted server)."""
    purpose = purpose or PURPOSES.get(schema_name, f"structured output: {schema_name}")
    if not open_weights and not glimmer and routes_open(schema_name):
        open_weights = True  # OPEN_WEIGHTS_STAGES routes this text stage to Muse Spark Open
    cost.check(CHAT_RESERVE_USD)
    rf: dict[str, Any] = {"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema}}
    if glimmer:
        # Muse Glimmer docs: OpenAI chat-completions wire format; reasons before answering, so leave max_tokens
        # headroom; never send temperature 0 (greedy loops); some runtimes reject reasoning_effort, so omit it.
        url = f"{settings.glimmer_api_base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if settings.glimmer_api_key or settings.fake_meta:
            headers["Authorization"] = f"Bearer {_key(settings.glimmer_api_key)}"
        body: dict[str, Any] = {"model": settings.glimmer_model, "messages": messages, "response_format": rf,
                                "max_tokens": 8192}
        try:
            r = _post(url, headers=headers, json=body, timeout=600, purpose=purpose)
        except MetaAPIError as e:
            if "response_format" not in str(e) and "json_schema" not in str(e):
                raise
            body["response_format"] = {"type": "json_object"}  # provider without json_schema support
            r = _post(url, headers=headers, json=body, timeout=600, purpose=purpose)
        j = r.json()
        cost.count_tokens(settings.glimmer_model, j.get("usage"))  # billed by the host, not by Meta
        return _extract_json(j["choices"][0]["message"].get("content") or "")
    if open_weights:
        url = f"{settings.open_api_base}/chat/completions"
        headers = {"Authorization": f"Bearer {_key(settings.baseten_api_key)}", "Content-Type": "application/json"}
        body = {
            "model": settings.open_model, "messages": messages, "response_format": rf,
            "max_tokens": 16384,  # reasoning and answer share this budget on Muse Spark Open
            "reasoning_effort": reasoning_effort if reasoning_effort in {"low", "medium", "high", "xhigh"} else "medium",
        }
    else:
        model = model or settings.lakon_model
        url = f"{settings.meta_api_base}/chat/completions"
        headers = _headers()
        body = {"model": model, "messages": messages, "reasoning_effort": reasoning_effort, "response_format": rf}
    try:
        r = _post(url, headers=headers, json=body, timeout=600, purpose=purpose)
    except MetaAPIError as e:
        if open_weights and "response_format" in str(e):  # provider only takes json_object
            body["response_format"] = {"type": "json_object"}
            r = _post(url, headers=headers, json=body, timeout=600, purpose=purpose)
        else:
            raise
    j = r.json()
    if not open_weights and model:
        cost.charge_tokens(model, j.get("usage"))
    elif open_weights:
        cost.count_tokens(settings.open_model, j.get("usage"))  # billed by the host (Baseten), not by Meta
    content = j["choices"][0]["message"].get("content") or ""
    if not content.strip() and not open_weights and body.get("reasoning_effort") != "low":
        # Seen live on muse-spark-1.3: reasoning can use the whole output budget and leave content null
        # (finish_reason "length"). Ask once more with less reasoning instead of failing the film.
        log.warning("empty content from %s (finish_reason %s), retrying with reasoning_effort=low", model,
                    j["choices"][0].get("finish_reason"))
        body["reasoning_effort"] = "low"
        j = _post(url, headers=headers, json=body, timeout=600, purpose=purpose + " (retry, less reasoning)").json()
        if model:
            cost.charge_tokens(model, j.get("usage"))
        content = j["choices"][0]["message"].get("content") or ""
    if not content.strip():
        raise MetaAPIError(f"{model or settings.open_model} returned no content "
                           f"(finish_reason {j['choices'][0].get('finish_reason')})")
    return _extract_json(content)


# --------------------------------------------------------------------------- 3/5. Muse Image
def _image_bytes(r: httpx.Response) -> bytes:
    data = r.json().get("data") or []
    if not data:
        raise MetaAPIError(f"Muse Image returned no image: {r.text[:300]}")
    if data[0].get("b64_json"):
        return base64.b64decode(data[0]["b64_json"])
    if data[0].get("url"):
        return client().get(data[0]["url"], timeout=120).content
    raise MetaAPIError("Muse Image response had neither b64_json nor url")


def generate_image(prompt: str, out: Path, size: str = "1536x1024", fast: bool = False,
                   purpose: str = "generate picture") -> Path:
    cost.check(cost.IMAGE_USD)
    body = {
        "model": settings.image_model, "prompt": prompt, "n": 1, "size": size, "output_format": "png",
        "reasoning_strength": "low" if fast else "high",
        # Art, not facts: keep image search (wayang style references), turn off web search and shell.
        "tool_enablement": {"enable_web_search": False, "enable_shell": False, "enable_image_search": True},
    }
    r = _post(f"{settings.meta_api_base}/images/generations", headers=_headers(), json=body, timeout=600,
              purpose=purpose)
    fileio.atomic_write_bytes(out, _image_bytes(r))  # a reader never sees a half-written picture
    cost.charge(settings.image_model, cost.IMAGE_USD)
    return out


def edit_image(prompt: str, refs: list[Path], out: Path, fast: bool = False,
               purpose: str = "edit picture from references") -> Path:
    """Image-to-image with 1-10 reference images (Meta's JSON body for /v1/images/edits)."""
    cost.check(cost.IMAGE_USD)
    body = {
        "model": settings.image_model, "prompt": prompt, "n": 1, "output_format": "png",
        "images": [{"image_url": data_url(p)} for p in refs[:10]],
        "reasoning_strength": "low" if fast else "high",
        "tool_enablement": {"enable_web_search": False, "enable_shell": False},
    }
    r = _post(f"{settings.meta_api_base}/images/edits", headers=_headers(), json=body, timeout=600,
              purpose=purpose)
    fileio.atomic_write_bytes(out, _image_bytes(r))  # a reader never sees a half-written picture
    cost.charge(settings.image_model, cost.IMAGE_USD)
    return out


# --------------------------------------------------------------------------- 4. SAM 3.1
def segment(image_path: Path, phrase: str) -> list[dict[str, Any]]:
    """SAM 3.1 concept prompt. Returns [{left, top, right, bottom, mask (bytes 0/1, mh x mw), confidence}].
    Masks are box-local; parsed with Meta's own parser (pip install meta-sam-parser)."""
    cost.check(cost.SAM_IMAGE_USD)
    body = {
        "model": settings.sam_model,
        "input": [{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": phrase},
            {"type": "input_image", "image_url": data_url(image_path)},
        ]}],
        "stream": True,
        "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"},  # metadata values are strings
    }
    events: list[dict[str, Any]] = []
    headers = _headers() | {"Accept": "text/event-stream"}
    t0 = time.monotonic()
    tried = 0
    brk = resilience.breaker(settings.sam_model)
    if not brk.allow():
        cost.record_call(settings.sam_model, "/v1/responses", f"cut out \"{phrase}\"", 0, 0, False, "circuit open")
        raise MetaAPIError(f"circuit open for {settings.sam_model}")
    for attempt in range(3):
        tried = attempt + 1
        events.clear()
        try:
            with client().stream("POST", f"{settings.meta_api_base}/responses", headers=headers, json=body, timeout=300) as r:
                if r.status_code in RETRY_STATUS and attempt < 2:
                    time.sleep(resilience.backoff(attempt, r.headers.get("retry-after")))
                    continue
                if r.status_code >= 400:
                    r.read()
                    cost.record_call(settings.sam_model, "/v1/responses", f"cut out \"{phrase}\"",
                                     (time.monotonic() - t0) * 1000, tried, False, f"HTTP {r.status_code}")
                    if r.status_code in RETRY_STATUS:
                        brk.failure()
                    raise MetaAPIError(f"SAM {r.status_code}: {r.text[:400]}")
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        events.append(json.loads(payload))
            break
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == 2:
                cost.record_call(settings.sam_model, "/v1/responses", f"cut out \"{phrase}\"",
                                 (time.monotonic() - t0) * 1000, tried, False, "timeout")
                brk.failure()
                raise
            time.sleep(resilience.backoff(attempt))
    cost.record_call(settings.sam_model, "/v1/responses", f"cut out \"{phrase}\" (streamed masks)",
                     (time.monotonic() - t0) * 1000, tried, True)
    brk.success()
    cost.charge(settings.sam_model, cost.SAM_IMAGE_USD)
    return parse_sam_events(events)


def parse_sam_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Responses stream events -> masks, using Meta's meta-sam-parser."""
    from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream

    async def _source():
        for ev in events:
            yield ev

    async def _parse():
        return await parse_responses_stream(_source(), image_segmentation_format()).final_result()

    result = asyncio.run(_parse())
    out: list[dict[str, Any]] = []
    for rec in result.records:
        if rec.kind != "mask":
            continue
        b = rec.bounds
        out.append({
            "object_id": rec.object_id, "left": int(b.left), "top": int(b.top), "right": int(b.right),
            "bottom": int(b.bottom), "mask": decode_mask_to_raster(rec.mask), "mw": rec.mask.width,
            "mh": rec.mask.height, "confidence": rec.confidence,
        })
    return out
