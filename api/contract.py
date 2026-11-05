"""The documented request/response shapes of every Meta call Dalang AI makes, as machine-checkable rules.

Source of every rule: Meta's docs as read on 2026-10-30, 2026-10-31 and 2026-11-02 (see docs/META_MODELS.md,
"Contract tests"). Nothing here is guessed: a field is listed only if a docs page shows it.
  * Images      https://dev.meta.ai/docs/image-generation  (top-level fields; "an unknown top-level field ... returns 400";
                edits: 1-10 `images` items, each exactly one of image_url | file_id; response {created, data[{b64_json|url}], ...})
  * Chat        https://dev.meta.ai/docs/structured-output, /docs/image-understanding, /docs/video-understanding#audio
  * ASR         https://dev.meta.ai/docs/speech-to-text  (multipart parts `request` + `audio`; response {transcript, turns[]})
  * SAM 3.1     https://dev.meta.ai/docs/media-segmentation (POST /v1/responses, stream, metadata strings)
  * Open weights https://dev.meta.ai/docs/muse-spark-open/deploy#baseten, /docs/muse-glimmer/deploy#hosted-providers

`check_request` / `check_response` return a list of human-readable violations (empty = OK). They are used by the
contract tests (tests/test_contract.py) and by `scripts/go_live.py --preflight` before any paid call goes out.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

DOCS = {
    "images": "https://dev.meta.ai/docs/image-generation",
    "chat": "https://dev.meta.ai/docs/structured-output",
    "asr": "https://dev.meta.ai/docs/speech-to-text",
    "sam": "https://dev.meta.ai/docs/media-segmentation",
}

IMAGE_FIELDS = {"model", "prompt", "n", "size", "response_format", "output_format", "reasoning_strength",
                "tool_enablement", "user", "stream"}
EDIT_FIELDS = IMAGE_FIELDS | {"images"}
TOOL_KEYS = {"enable_image_search", "enable_web_search", "enable_shell"}
META_MODELS = {"muse-spark-1.3", "muse-spark-1.2", "muse-spark-1.1", "muse-wonder-1.0", "muse-image-1.0", "sam-3.1",
               "muse-voice-transcribe-1.0"}
REASONING_EFFORT = {"low", "medium", "high", "xhigh"}
ASR_MODES = {"PUSH_TO_TALK", "ENDPOINTING", "DIARIZATION"}
SIZE_RE = re.compile(r"^(\d{2,5})x(\d{2,5})$|^auto$")


def _size_ok(size: str) -> bool:
    m = SIZE_RE.match(size)
    if not m:
        return False
    if size == "auto":
        return True
    w, h = int(m.group(1)), int(m.group(2))
    return max(w, h) / max(1, min(w, h)) <= 16  # "aspect ratios beyond 16:1 return 400"


def _images_common(body: dict[str, Any], allowed: set[str]) -> list[str]:
    errs = [f"unknown top-level field '{k}' (Meta returns 400)" for k in body if k not in allowed]
    if body.get("model") != "muse-image-1.0":
        errs.append(f"model must be muse-image-1.0, got {body.get('model')!r}")
    p = body.get("prompt")
    if not isinstance(p, str) or not p.strip():
        errs.append("prompt must be a non-empty string")
    n = body.get("n", 1)
    if not isinstance(n, int) or not 1 <= n <= 10:
        errs.append("n must be 1..10")
    if "size" in body and not _size_ok(str(body["size"])):
        errs.append(f"size {body['size']!r} must be 'WxH' with aspect <= 16:1, or 'auto'")
    if body.get("output_format", "webp") not in {"webp", "png", "jpeg"}:
        errs.append("output_format must be webp|png|jpeg")
    if body.get("response_format", "b64_json") not in {"b64_json", "url"}:
        errs.append("response_format must be b64_json|url")
    if body.get("reasoning_strength", "high") not in {"high", "low"}:
        errs.append("reasoning_strength must be high|low")
    te = body.get("tool_enablement")
    if te is not None:
        if not isinstance(te, dict) or any(k not in TOOL_KEYS or not isinstance(v, bool) for k, v in te.items()):
            errs.append("tool_enablement must only hold boolean enable_image_search/enable_web_search/enable_shell")
    return errs


def _content_parts_ok(messages: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(messages, list) or not messages:
        return ["messages must be a non-empty list"]
    for i, m in enumerate(messages):
        if m.get("role") not in {"system", "user", "assistant"}:
            errs.append(f"messages[{i}].role invalid")
        c = m.get("content")
        if isinstance(c, str):
            continue
        if not isinstance(c, list):
            errs.append(f"messages[{i}].content must be a string or a list of parts")
            continue
        for j, part in enumerate(c):
            t = part.get("type")
            if t == "text" and not isinstance(part.get("text"), str):
                errs.append(f"messages[{i}].content[{j}] text part needs 'text'")
            elif t == "image_url":
                url = (part.get("image_url") or {}).get("url") if isinstance(part.get("image_url"), dict) else None
                if not isinstance(url, str) or not (url.startswith("data:image/") or url.startswith("http")):
                    errs.append(f"messages[{i}].content[{j}] image_url must be an object {{url: data URL or https}}")
            elif t == "input_audio":
                ia = part.get("input_audio") or {}
                if not ia.get("data") or ia.get("format") not in {"wav", "mp3"}:
                    errs.append(f"messages[{i}].content[{j}] input_audio needs base64 data and format wav")
            elif t not in {"text", "image_url", "input_audio"}:
                errs.append(f"messages[{i}].content[{j}] unknown part type {t!r}")
    return errs


def _chat(body: dict[str, Any], host: str) -> list[str]:
    errs = _content_parts_ok(body.get("messages"))
    model = str(body.get("model", ""))
    rf = body.get("response_format")
    if rf is not None:
        if rf.get("type") == "json_schema":
            js = rf.get("json_schema") or {}
            if not js.get("name") or not isinstance(js.get("schema"), dict):
                errs.append("response_format.json_schema needs name and schema")
        elif rf.get("type") != "json_object":
            errs.append("response_format.type must be json_schema (or json_object on open-weight hosts)")
    if host == "api.meta.ai":
        if model not in META_MODELS or model.startswith(("muse-image", "sam", "muse-voice")):
            errs.append(f"chat model {model!r} is not a documented Meta text model")
        if "reasoning_effort" in body and body["reasoning_effort"] not in REASONING_EFFORT:
            errs.append("reasoning_effort must be low|medium|high|xhigh")
        has_audio = any(
            isinstance(m.get("content"), list) and any(p.get("type") == "input_audio" for p in m["content"])
            for m in body.get("messages") or [])
        if has_audio:
            if model != "muse-spark-1.2":
                errs.append("audio understanding must use muse-spark-1.2 (1.3 audio is 'not fully supported')")
            if int(body.get("max_tokens") or 0) < 4000:
                errs.append("audio understanding needs max_tokens >= 4000")
    elif host == "inference.baseten.co":
        if not model.startswith("meta-models/muse-spark-open"):
            errs.append(f"Baseten model must be meta-models/muse-spark-open[...], got {model!r}")
    elif host == "api.together.xyz":
        if model != "meta-models/Muse-Glimmer-30B":
            errs.append(f"Together model must be meta-models/Muse-Glimmer-30B, got {model!r}")
        if body.get("temperature") == 0:
            errs.append("Muse Glimmer: never send temperature 0")
    return errs


def _sam(body: dict[str, Any]) -> list[str]:
    errs = []
    if body.get("model") != "sam-3.1":
        errs.append("SAM model must be sam-3.1")
    if body.get("stream") is not True:
        errs.append("SAM requests must stream (stream: true)")
    md = body.get("metadata") or {}
    if any(not isinstance(v, str) for v in md.values()):
        errs.append("SAM metadata values must be strings")
    if md.get("mask_encoding") not in {None, "one_bit", "rle"}:
        errs.append("metadata.mask_encoding must be one_bit")
    try:
        content = body["input"][0]["content"]
        types = [p["type"] for p in content]
        if types.count("input_text") != 1 or types.count("input_image") != 1:
            errs.append("SAM input needs exactly one input_text (noun phrase) and one input_image")
        text = next(p["text"] for p in content if p["type"] == "input_text")
        if not text.strip() or len(text.split()) > 8:
            errs.append("SAM concept prompt must be a short noun phrase")
    except (KeyError, IndexError, TypeError, StopIteration):
        errs.append("SAM input must be [{type: message, role: user, content: [input_text, input_image]}]")
    return errs


def _asr(content: bytes, query: str) -> list[str]:
    errs = []
    if "sessionId=" not in query:
        errs.append("ASR needs a sessionId query parameter")
    if b'name="request"' not in content or b'name="audio"' not in content:
        return errs + ["ASR multipart needs parts 'request' and 'audio'"]
    m = re.search(rb'name="request"\r\n(?:[^\r\n]+\r\n)*\r\n(.*?)\r\n--', content, re.S)
    try:
        req = json.loads(m.group(1)) if m else {}
    except ValueError:
        req = {}
    if req.get("mode") not in ASR_MODES:
        errs.append("ASR request.mode must be PUSH_TO_TALK|ENDPOINTING|DIARIZATION")
    if req.get("model") != "muse-voice-transcribe-1.0":
        errs.append("ASR model must be muse-voice-transcribe-1.0")
    if req.get("audioEncoding") != "WAV":
        errs.append("ASR audioEncoding must be WAV")
    if "languageBias" in req and not isinstance(req["languageBias"], list):
        errs.append("languageBias must be a list of language names")
    if b"RIFF" not in content:
        errs.append("ASR audio part must be a WAV file")
    return errs


def check_request(method: str, url: str, headers: dict[str, str], content: bytes) -> list[str]:
    """Violations of the documented request shape for one outgoing HTTP request."""
    from urllib.parse import urlsplit

    u = urlsplit(url)
    path, host = u.path, u.hostname or ""
    errs: list[str] = []
    if method != "POST":
        errs.append(f"{path}: expected POST")
    auth = {k.lower(): v for k, v in headers.items()}.get("authorization", "")
    if host in {"api.meta.ai", "inference.baseten.co"} and not auth.startswith("Bearer "):
        errs.append(f"{path}: missing 'Authorization: Bearer <key>'")
    if path.endswith("/asr/transcribe"):
        return errs + _asr(content, u.query)
    try:
        body = json.loads(content or b"{}")
    except ValueError:
        return errs + [f"{path}: body is not JSON"]
    if path.endswith("/images/generations"):
        errs += _images_common(body, IMAGE_FIELDS)
    elif path.endswith("/images/edits"):
        errs += _images_common(body, EDIT_FIELDS)
        imgs = body.get("images")
        if not isinstance(imgs, list) or not 1 <= len(imgs) <= 10:
            errs.append("edits need 1-10 images")
        else:
            for i, it in enumerate(imgs):
                if not isinstance(it, dict) or sorted(it) not in (["image_url"], ["file_id"]):
                    errs.append(f"images[{i}] must contain exactly one of image_url | file_id")
    elif path.endswith("/chat/completions"):
        errs += _chat(body, host)
    elif path.endswith("/responses"):
        errs += _sam(body)
    else:
        errs.append(f"{path}: not an endpoint Dalang AI is documented to call")
    return errs


def check_response(path: str, status: int, body: Any) -> list[str]:
    """Violations of the documented response shape (used on fixtures and recorded real replies)."""
    if status >= 400:
        err = body.get("error") if isinstance(body, dict) else None
        return [] if isinstance(err, dict) and "message" in err else [f"{path}: error body lacks error.message"]
    if path.endswith("/images/generations") or path.endswith("/images/edits"):
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or not data or not (data[0].get("b64_json") or data[0].get("url")):
            return [f"{path}: expected data[0].b64_json or data[0].url"]
        return []
    if path.endswith("/chat/completions"):
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return [f"{path}: expected choices[0].message.content"]
        return [] if isinstance(content, str) else [f"{path}: message.content must be a string"]
    if path.endswith("/asr/transcribe"):
        if not isinstance(body, dict) or not isinstance(body.get("transcript"), str):
            return [f"{path}: expected transcript string"]
        bad = [t for t in body.get("turns") or [] if not {"startMs", "endMs"} <= set(t)]
        return [f"{path}: turns need startMs/endMs"] if bad else []
    return []


class Guard(httpx.BaseTransport):
    """An httpx transport wrapper that refuses (locally, without sending) any request breaking the documented
    shape, so a malformed request never costs money or trips a rate limit. Used by go_live --preflight."""

    def __init__(self, inner: httpx.BaseTransport):
        self.inner = inner
        self.violations: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        errs = check_request(request.method, str(request.url), dict(request.headers), request.content)
        if errs:
            self.violations += errs
            return httpx.Response(400, json={"error": {"message": "refused locally by the contract guard: "
                                                                  + "; ".join(errs)}}, request=request)
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()
