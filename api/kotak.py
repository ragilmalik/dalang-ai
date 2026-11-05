"""Kotak Wayang (the puppet box): a family's SAM 3.1 cut-outs, kept so the same puppets can come back in the
next story ("bring back Kancil"). No accounts: the browser makes a random family id and keeps it in
localStorage; only generated puppet pictures and their descriptions are stored, never recordings or names."""
from __future__ import annotations

import re
import secrets
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from . import db
from .config import settings

FAMILY_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
MAX_PUPPETS = 40

_lock = threading.Lock()
_store = db.Store([
    "CREATE TABLE IF NOT EXISTS puppets (id TEXT PRIMARY KEY, family TEXT, created REAL, char_id TEXT, name TEXT, "
    "kind TEXT, archetype TEXT, look TEXT, sam_phrase TEXT, note TEXT, source_job TEXT)",
    "CREATE INDEX IF NOT EXISTS puppets_family ON puppets(family)",
])  # same database file and setup as api/db.py (WAL, busy timeout, reconnect if the file is replaced)
COLS = ("id", "family", "created", "char_id", "name", "kind", "archetype", "look", "sam_phrase", "note", "source_job")


def valid_family(fid: str | None) -> bool:
    return bool(fid) and bool(FAMILY_RE.match(fid or ""))


def folder(family: str) -> Path:
    return settings.data_dir / "kotak" / family


def image_url(p: dict[str, Any]) -> str:
    return f"/api/kotak/{p['family']}/{p['id']}.png"


def _public(p: dict[str, Any]) -> dict[str, Any]:
    return {**{k: p[k] for k in COLS if k != "family"}, "cutout": image_url(p)}


def list_family(family: str) -> list[dict[str, Any]]:
    with _lock:
        conn = _store.get()
        rows = conn.execute(f"SELECT {','.join(COLS)} FROM puppets WHERE family=? ORDER BY created DESC",  # nosec B608
                             (family,)).fetchall()
    return [_public(dict(zip(COLS, r, strict=True))) for r in rows]


def get(family: str, pid: str) -> dict[str, Any] | None:
    with _lock:
        conn = _store.get()
        r = conn.execute(f"SELECT {','.join(COLS)} FROM puppets WHERE family=? AND id=?",  # nosec B608
                          (family, pid)).fetchone()
    return dict(zip(COLS, r, strict=True)) if r else None


def save_from_job(family: str, job_state: dict[str, Any], job_dir: Path, char_id: str) -> dict[str, Any]:
    script = job_state.get("script") or {}
    char = next((c for c in script.get("characters", []) if c["id"] == char_id), None)
    cut = job_dir / "puppets" / f"{char_id}.png"
    if char is None or not cut.exists():
        raise KeyError("No such puppet in this film")
    existing = [p for p in list_family(family) if p["char_id"] == char_id and p["source_job"] == job_state["id"]]
    if existing:
        return existing[0]
    if len(list_family(family)) >= MAX_PUPPETS:
        raise OverflowError(f"The puppet box holds {MAX_PUPPETS} puppets; remove one first.")
    pid = secrets.token_hex(6)
    d = folder(family)
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cut, d / f"{pid}.png")
    sheet = job_dir / "sheets" / f"{char_id}.png"
    if sheet.exists():
        shutil.copyfile(sheet, d / f"{pid}_sheet.png")
    row = {"id": pid, "family": family, "created": time.time(), "char_id": char_id, "name": char["name"],
           "kind": char.get("kind", "human"), "archetype": char.get("wayang_archetype", ""),
           "look": char.get("visual_description", ""), "sam_phrase": char.get("sam_phrase", "puppet"),
           "note": char.get("cultural_note", ""), "source_job": job_state["id"]}
    with _lock:
        conn = _store.get()
        conn.execute(f"INSERT INTO puppets({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})",  # nosec B608
                      tuple(row[k] for k in COLS))
        conn.commit()
    return _public(row)


def delete(family: str, pid: str) -> bool:
    with _lock:
        conn = _store.get()
        n = conn.execute("DELETE FROM puppets WHERE family=? AND id=?", (family, pid)).rowcount
        conn.commit()
    for f in (folder(family) / f"{pid}.png", folder(family) / f"{pid}_sheet.png"):
        f.unlink(missing_ok=True)
    return n > 0


def resolve(family: str, ids: list[str]) -> list[dict[str, Any]]:
    """The returning puppets a new story asked for (unknown ids are ignored), at most 3."""
    out = []
    for pid in ids[:3]:
        p = get(family, pid)
        if p:
            out.append(p)
    return out


def bring_into_job(p: dict[str, Any], job_dir: Path, char_id: str) -> bool:
    """Copy a returning puppet's cut-out (and sheet) into a job under the script's character id."""
    src = folder(p["family"]) / f"{p['id']}.png"
    if not src.exists():
        return False
    (job_dir / "puppets").mkdir(exist_ok=True)
    (job_dir / "sheets").mkdir(exist_ok=True)
    shutil.copyfile(src, job_dir / "puppets" / f"{char_id}.png")
    sheet = folder(p["family"]) / f"{p['id']}_sheet.png"
    shutil.copyfile(sheet if sheet.exists() else src, job_dir / "sheets" / f"{char_id}.png")
    return True
