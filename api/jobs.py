"""Job state, persisted to SQLite and pushed to the browser over Server-Sent Events."""
from __future__ import annotations

import logging
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from . import db, errors
from .config import settings

log = logging.getLogger("dalang.jobs")

STAGES = [
    ("listen", "Listening"),
    ("lakon", "Writing the lakon"),
    ("casting", "Casting the puppets"),
    ("scenes", "Painting the scenes"),
    ("animate", "Bringing them to life"),
    ("narrate", "Narrating"),
    ("cut", "Final cut"),
]


class Job:
    """Wraps the job's JSON state with helpers. Every change is saved and bumps a version for SSE."""

    _live: dict[str, Job] = {}
    _guard = threading.Lock()

    def __init__(self, state: dict[str, Any]):
        self.s = state
        self.lock = threading.RLock()
        self.version = 0
        self.changed = threading.Condition()

    # ------------------------------------------------------------------ lifecycle
    @classmethod
    def create(cls, language: str, style: str, review: bool, gara_gara: bool = False, narration_voice: str = "tts",
               **extra: Any) -> Job:
        jid = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")
        state = {
            "id": jid, "created": time.time(), "status": "queued", "language": language, "style": style,
            "review": review, "public": False, "title": "", "transcript": "", "script": None,
            "stages": [{"key": k, "label": label, "status": "pending", "detail": "", "thumbs": []} for k, label in STAGES],
            "scenes": [], "cast": [], "videos": {}, "poster": None, "cost_usd": 0.0, "error": None,
            "message": None, "demo_replay": False, "models": [], "offline": settings.offline,
            "gara_gara": {"enabled": bool(gara_gara), "status": "off" if not gara_gara else "pending"},
            "part1": None, "narration_voice": narration_voice if narration_voice in {"tts", "child"} else "tts",
            **extra,
        }
        job = cls(state)
        job.dir.mkdir(parents=True, exist_ok=True)
        with cls._guard:
            cls._live[jid] = job
        job.save()
        return job

    @classmethod
    def get(cls, jid: str) -> Job | None:
        with cls._guard:
            if jid in cls._live:
                return cls._live[jid]
        state = db.load(jid)
        if not state:
            return None
        job = cls(state)
        with cls._guard:
            cls._live[jid] = job
        return job

    @classmethod
    def forget(cls, jid: str) -> None:
        """Drop a deleted job from the in-memory cache."""
        with cls._guard:
            cls._live.pop(jid, None)

    @property
    def id(self) -> str:
        return self.s["id"]

    @property
    def dir(self) -> Path:
        return settings.data_dir / "jobs" / self.s["id"]

    def url(self, path: Path | str) -> str:
        rel = Path(path).relative_to(self.dir) if isinstance(path, Path) and Path(path).is_absolute() else Path(path)
        return f"/media/{self.id}/{rel.as_posix()}?v={int(time.time())}"

    # ------------------------------------------------------------------ updates
    def save(self) -> None:
        with self.lock:
            db.save(self.s)
        with self.changed:
            self.version += 1
            self.changed.notify_all()

    def stage(self, key: str, status: str | None = None, detail: str | None = None, thumb: str | None = None,
              clear_thumbs: bool = False) -> None:
        with self.lock:
            st = next(s for s in self.s["stages"] if s["key"] == key)
            if status:
                now = time.time()
                if status == "running" and st["status"] != "running":
                    st["started"] = now
                if status in {"done", "failed", "skipped"} and st.get("started"):
                    st["seconds"] = round(now - st["started"], 1)
                    log.info("stage %s %s in %.1f s", key, status, st["seconds"],
                             extra={"job_id": self.id, "stage": key, "stage_status": status, "seconds": st["seconds"]})
                st["status"] = status
            if detail is not None:
                st["detail"] = errors.scrub(detail)
            if clear_thumbs:
                st["thumbs"] = []
            if thumb:
                st["thumbs"].append(thumb)
        self.save()

    def set(self, **kw: Any) -> None:
        for k in ("error", "message"):  # never a server path or an exception class name in what a family sees
            if isinstance(kw.get(k), str):
                kw[k] = errors.scrub(kw[k])
        with self.lock:
            self.s.update(kw)
        self.save()

    def used(self, model: str) -> None:
        with self.lock:
            if model not in self.s["models"]:
                self.s["models"].append(model)

    def wait_change(self, seen: int, timeout: float = 15.0) -> int:
        with self.changed:
            if self.version == seen:
                self.changed.wait(timeout)
            return self.version
