"""Go-live safety net around every Meta call: jittered back-off, a circuit breaker per model, a process-wide
spend ledger with hard caps, recorded-fixture record/replay, and a helper that records a stage's graceful fallback.

Environment:
  MAX_USD_PER_FILM   hard cap per film (alias of JOB_BUDGET_USD; default 1.50)
  MAX_USD_TOTAL      hard cap for everything this deployment spends on Meta, persisted in DATA_DIR/spend_total.json
                     (default 25; 0 = no cap). Only real calls count; fake-API "would cost" amounts never do.
  BREAKER_THRESHOLD  consecutive failed calls (after retries) that open a model's breaker (default 4)
  BREAKER_COOLDOWN_S seconds an open breaker waits before letting one trial call through (default 60)
  META_RECORD_DIR    record every Meta request/response pair (keys redacted, images hashed) as fixtures
  META_REPLAY_DIR    answer every Meta call from those fixtures instead of the network (no key, no cost)
"""
from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from .config import _env

# --------------------------------------------------------------------------- back-off
JITTER = 0.25


def backoff(attempt: int, retry_after: str | None = None) -> float:
    """Seconds to wait before retry `attempt` (0-based): 2, 4, 8 ... plus up to 25 % jitter, so parallel scene
    painters do not retry in lock-step; a server's Retry-After (seconds, capped at 30) wins when it is longer."""
    base = 2 ** attempt * 2
    wait = base * (1 + random.random() * JITTER)
    if retry_after:
        try:
            wait = max(wait, min(30.0, float(retry_after)))
        except ValueError:
            pass
    return round(wait, 2)


# --------------------------------------------------------------------------- circuit breaker
class CircuitOpen(RuntimeError):
    pass


class Breaker:
    """closed -> (threshold consecutive failures) -> open -> (cooldown) -> half_open -> one trial call ->
    closed on success, open again on failure. Per model, shared by every film in this process."""

    def __init__(self, threshold: int, cooldown: float):
        self.threshold, self.cooldown = threshold, cooldown
        self.fails = 0
        self.opened_at: float | None = None
        self.lock = threading.Lock()

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half_open" if time.monotonic() - self.opened_at >= self.cooldown else "open"

    def allow(self) -> bool:
        with self.lock:
            return self.state != "open"

    def success(self) -> None:
        with self.lock:
            self.fails, self.opened_at = 0, None

    def failure(self) -> None:
        with self.lock:
            self.fails += 1
            if self.fails >= self.threshold or self.opened_at is not None:
                self.opened_at = time.monotonic()


_breakers: dict[str, Breaker] = {}
_blk = threading.Lock()


def breaker(model: str) -> Breaker:
    with _blk:
        if model not in _breakers:
            _breakers[model] = Breaker(int(_env("BREAKER_THRESHOLD", default="4")),
                                       float(_env("BREAKER_COOLDOWN_S", default="60")))
        return _breakers[model]


def breaker_states() -> dict[str, str]:
    with _blk:
        return {m: b.state for m, b in _breakers.items()}


def reset_breakers() -> None:
    with _blk:
        _breakers.clear()


# --------------------------------------------------------------------------- spend ledger
class Ledger:
    """What this deployment has spent on real Meta calls, across films and restarts."""

    def __init__(self) -> None:
        self.lock = threading.Lock()

    @property
    def path(self) -> Path:
        from .config import settings

        return settings.data_dir / "spend_total.json"

    @property
    def cap(self) -> float | None:
        v = float(_env("MAX_USD_TOTAL", default="25"))
        return v if v > 0 else None

    def total(self) -> float:
        try:
            return float(json.loads(self.path.read_text()).get("usd", 0.0))
        except (OSError, ValueError):
            return 0.0

    def add(self, usd: float) -> None:
        with self.lock:
            t = self.total() + usd
            self.path.write_text(json.dumps({"usd": round(t, 6), "updated": time.time()}))

    def room(self, upcoming: float) -> bool:
        cap = self.cap
        return cap is None or self.total() + upcoming <= cap


ledger = Ledger()


# --------------------------------------------------------------------------- record / replay
_B64ISH = re.compile(r"^(data:[^;]+;base64,)?[A-Za-z0-9+/=\s]{400,}$")


def _redact(v: Any) -> Any:
    """Long base64 strings (images, audio) become their hash, so fixtures stay small and hold no user media."""
    if isinstance(v, dict):
        return {k: _redact(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_redact(x) for x in v]
    if isinstance(v, str) and len(v) > 400 and _B64ISH.match(v[:2000]):
        return "sha256:" + hashlib.sha256(v.encode()).hexdigest()[:16]
    return v


def _body_of(request: httpx.Request) -> tuple[Any, bytes]:
    content = request.content
    ctype = request.headers.get("content-type", "")
    if "multipart" in ctype:
        boundary = ctype.split("boundary=")[-1].encode()
        stripped = content.replace(boundary, b"")
        m = re.search(rb'name="request"\r\n(?:[^\r\n]+\r\n)*\r\n(.*?)\r\n', content, re.S)
        req = json.loads(m.group(1)) if m else {}
        return {"multipart_request": req, "audio_sha": hashlib.sha256(stripped).hexdigest()[:16]}, stripped
    try:
        return json.loads(content or b"{}"), content
    except ValueError:
        return {}, content


def fixture_keys(request: httpx.Request) -> tuple[str, str]:
    """(exact key, loose key). Exact: endpoint + whole redacted body. Loose: endpoint + model + schema name, used
    when an exact match is missing (a prompt that changed by one word still gets a well-formed reply)."""
    body, _ = _body_of(request)
    path = request.url.path
    exact = hashlib.sha256((request.url.host + path + json.dumps(_redact(body), sort_keys=True)).encode()).hexdigest()[:24]
    model = body.get("model") or (body.get("multipart_request") or {}).get("model", "")
    schema = ((body.get("response_format") or {}).get("json_schema") or {}).get("name", "")
    has_audio = "input_audio" in json.dumps(_redact(body.get("messages", [])))
    loose = f"{request.url.host}{path}|{model}|{schema}|{'audio' if has_audio else ''}"
    return exact, loose


class RecordingTransport(httpx.BaseTransport):
    """Wraps the real (or fake) transport and writes each exchange to META_RECORD_DIR/<exact>.json."""

    def __init__(self, inner: httpx.BaseTransport, folder: Path):
        self.inner, self.folder = inner, folder
        folder.mkdir(parents=True, exist_ok=True)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        resp = self.inner.handle_request(request)
        raw = resp.read()
        exact, loose = fixture_keys(request)
        body, _ = _body_of(request)
        (self.folder / f"{exact}.json").write_text(json.dumps({
            "loose": loose, "method": request.method, "url": str(request.url.copy_with(query=None)),
            "request": _redact(body), "status": resp.status_code,
            "content_type": resp.headers.get("content-type", "application/json"),
            "body_b64": base64.b64encode(raw).decode(), "recorded": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False))
        return httpx.Response(resp.status_code, headers={"content-type": resp.headers.get("content-type", "")},
                              content=raw, request=request)


class ReplayTransport(httpx.BaseTransport):
    """Serves recorded fixtures: exact match first, then the newest fixture with the same loose key."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.exact: dict[str, dict[str, Any]] = {}
        self.loose: dict[str, dict[str, Any]] = {}
        for f in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime):
            rec = json.loads(f.read_text())
            self.exact[f.stem] = rec
            self.loose[rec.get("loose", "")] = rec
        self.misses: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        exact, loose = fixture_keys(request)
        rec = self.exact.get(exact) or self.loose.get(loose)
        if rec is None:
            self.misses.append(loose)
            return httpx.Response(404, json={"error": {"message": f"no recorded fixture for {loose}"}}, request=request)
        return httpx.Response(rec["status"], headers={"content-type": rec["content_type"]},
                              content=base64.b64decode(rec["body_b64"]), request=request)


# --------------------------------------------------------------------------- graceful stage fallback
def fallback(job: Any, stage: str, label: str, what: str, placeholder: bool = True) -> None:
    """Record that a stage kept the film going without a model's output (shown on the film and in the trace)."""
    from . import cost
    from .errors import scrub

    what = scrub(what)
    cost.record_decision(f"{what}", agent="fallback")
    with job.lock:
        rows = list(job.s.get("fallbacks") or [])
        rows.append({"stage": stage, "label": label, "what": what, "placeholder": placeholder})
        job.s["fallbacks"] = rows
    job.save()
