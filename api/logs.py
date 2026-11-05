"""Structured logging: every line carries the request id and the film (job) id it belongs to, and secrets are scrubbed.

    LOG_FORMAT=json   one JSON object per line (for a log service): ts, level, logger, msg, request_id, job_id, + extras
    LOG_FORMAT=text   the default, readable in a terminal, with [rid=... job=...] when known
    LOG_LEVEL=INFO

Never logged: API keys (anything after "Bearer ", key-like tokens), story text, transcripts, recordings. Callers
log ids, stages, model names, timings and status codes only.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import time
from typing import Any

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
job_id: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="")

_SECRET = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+|\b(sk|pk|key|tok)[-_][A-Za-z0-9]{12,}\b|"
                     r"(api[_-]?key|authorization|token|secret|password)(\"?\s*[:=]\s*\"?)(?:bearer\s+)?[^\s\",}]+")
RID = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")
_EXTRA_SKIP = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def scrub(text: str) -> str:
    """Remove anything that looks like a credential from a log message."""
    def repl(m: re.Match[str]) -> str:
        if m.group(1):
            return m.group(1) + "[redacted]"
        if m.group(3):
            return m.group(3) + m.group(4) + "[redacted]"
        return "[redacted]"
    return _SECRET.sub(repl, text)


class ContextFilter(logging.Filter):
    """Adds request_id / job_id to every record and scrubs secrets from the message."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", "") or request_id.get()
        record.job_id = getattr(record, "job_id", "") or job_id.get()
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001 - a bad format string must not lose the line
            msg = str(record.msg)
        clean = scrub(msg)
        if clean != msg or record.args:
            record.msg, record.args = clean, None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
            "level": record.levelname, "logger": record.name, "msg": record.getMessage(),
        }
        for k in ("request_id", "job_id"):
            if getattr(record, k, ""):
                out[k] = getattr(record, k)
        for k, v in vars(record).items():
            if k not in _EXTRA_SKIP and k not in out and k not in {"request_id", "job_id"}:
                out[k] = v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
        if record.exc_info:
            out["exc"] = scrub(self.formatException(record.exc_info))
        return json.dumps(out, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s%(ctx)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        rid, jid = getattr(record, "request_id", ""), getattr(record, "job_id", "")
        parts = [f"rid={rid}"] if rid else []
        if jid:
            parts.append(f"job={jid}")
        record.ctx = f" [{' '.join(parts)}]" if parts else ""
        text = super().format(record)
        return scrub(text) if record.exc_info else text


def setup() -> None:
    """Configure the root logger once (idempotent)."""
    root = logging.getLogger()
    if any(isinstance(f, ContextFilter) for h in root.handlers for f in h.filters):
        return
    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter() if os.getenv("LOG_FORMAT", "text").lower() == "json" else TextFormatter())
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.StreamHandler)] + [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
