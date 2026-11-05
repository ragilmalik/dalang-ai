"""SQLite: one row per job (spec §8). The job's full state is a JSON document."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .config import settings

_lock = threading.Lock()
DB_FILE = "dalang.db"
SCHEMA = [
    "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created REAL, updated REAL, status TEXT, "
    "public INTEGER DEFAULT 0, title TEXT, data TEXT)",
    "CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, created REAL, "
    "rating INTEGER, comment TEXT, page TEXT)",
]
BUSY_TIMEOUT_S = 15.0


def connect(schema: list[str]) -> sqlite3.Connection:
    """One connection to DATA_DIR/dalang.db, set up for several threads and processes at once: WAL journal (readers
    never block the writer), a 15 s busy timeout instead of an instant "database is locked", synchronous=NORMAL."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.data_dir / DB_FILE, check_same_thread=False, timeout=BUSY_TIMEOUT_S)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_S * 1000)}")
    conn.execute("PRAGMA synchronous=NORMAL")
    for stmt in schema:
        conn.execute(stmt)
    conn.commit()
    return conn


def _file_id() -> tuple[int, int] | None:
    try:
        st = (settings.data_dir / DB_FILE).stat()
    except FileNotFoundError:
        return None
    return st.st_dev, st.st_ino


class Store:
    """A self-healing connection. If the database file is deleted or replaced while the app runs (for example a
    second test run clearing DATA_DIR), the old handle would fail with "attempt to write a readonly database";
    `get()` notices the file changed and reconnects, recreating the tables. Call it under the module's lock."""

    def __init__(self, schema: list[str]) -> None:
        self.schema = schema
        self.conn = connect(schema)
        self.file = _file_id()

    def get(self) -> sqlite3.Connection:
        now = _file_id()
        if now is None or now != self.file:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
            self.conn = connect(self.schema)
            self.file = _file_id()
        return self.conn


_store = Store(SCHEMA)


def add_feedback(job_id: str, rating: int, comment: str, page: str) -> int:
    with _lock:
        conn = _store.get()
        cur = conn.execute("INSERT INTO feedback(job_id, created, rating, comment, page) VALUES (?,?,?,?,?)",
                            (job_id, time.time(), rating, comment, page))
        conn.commit()
        return int(cur.lastrowid or 0)


def feedback_summary() -> dict[str, Any]:
    with _lock:
        conn = _store.get()
        rows = conn.execute("SELECT rating, COUNT(*), SUM(CASE WHEN comment<>'' THEN 1 ELSE 0 END) FROM feedback "
                             "GROUP BY rating").fetchall()
        pages = conn.execute("SELECT page, COUNT(*) FROM feedback GROUP BY page").fetchall()
    by = {str(k): 0 for k in range(1, 6)}
    total = comments = 0
    weighted = 0
    for rating, n, c in rows:
        by[str(rating)] = int(n)
        total += int(n)
        comments += int(c or 0)
        weighted += int(rating) * int(n)
    return {"count": total, "by_rating": by, "average": round(weighted / total, 2) if total else None,
            "with_comment": comments, "by_page": {p: int(n) for p, n in pages}}


def save(job: dict[str, Any]) -> None:
    job["updated"] = time.time()
    with _lock:
        conn = _store.get()
        conn.execute(
            "INSERT INTO jobs(id, created, updated, status, public, title, data) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET updated=excluded.updated, status=excluded.status, "
            "public=excluded.public, title=excluded.title, data=excluded.data",
            (job["id"], job["created"], job["updated"], job["status"], int(job.get("public", False)),
             job.get("title", ""), json.dumps(job)),
        )
        conn.commit()


def load(job_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _store.get()
        row = conn.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
    return json.loads(row[0]) if row else None


def gallery(limit: int = 60) -> list[dict[str, Any]]:
    with _lock:
        conn = _store.get()
        rows = conn.execute(
            "SELECT data FROM jobs WHERE public=1 AND status='done' ORDER BY updated DESC LIMIT ?", (limit,)
        ).fetchall()
    return [json.loads(r[0]) for r in rows]


def with_status(statuses: set[str] | list[str]) -> list[dict[str, Any]]:
    """Every job whose status is one of `statuses` (used to recover jobs a restart cut short)."""
    marks = ",".join("?" * len(statuses))
    with _lock:
        conn = _store.get()
        rows = conn.execute(f"SELECT data FROM jobs WHERE status IN ({marks})", tuple(statuses)).fetchall()  # nosec B608
    return [json.loads(r[0]) for r in rows]


def older_than(cutoff: float) -> list[dict[str, Any]]:
    """Jobs last updated before `cutoff` (unix time)."""
    with _lock:
        conn = _store.get()
        rows = conn.execute("SELECT data FROM jobs WHERE updated < ?", (cutoff,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def delete(job_id: str) -> None:
    with _lock:
        conn = _store.get()
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
