"""Safe file writes for pictures that several threads (or two films with the same story) may touch at once.

A plain `path.write_bytes()` truncates first and writes after, so a reader in between sees an empty or half
written file; on the shared FUSE disk it can even read the right length of zero bytes. Every picture is written
to a private temp file next to its target and moved into place with os.replace, which is atomic: a reader sees
the old file or the new one, never a torn one."""
from __future__ import annotations

import os
import threading
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    """Write `data` to `path` atomically (temp file in the same folder, fsync, os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def atomic_copy(src: Path, dst: Path) -> Path:
    """Copy through Python's own read/write (not sendfile, which read zeros on the FUSE disk) and replace atomically."""
    return atomic_write_bytes(dst, src.read_bytes())


def image_ok(path: Path) -> bool:
    """True when `path` is a complete picture PIL can read (header + chunk checksums)."""
    from PIL import Image

    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001 - any read failure means "not a usable picture"
        return False
