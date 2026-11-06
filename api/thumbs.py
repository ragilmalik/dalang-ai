"""Small card-size posters for the gallery and Pentas grids.

Why: a film's poster.jpg is 1200x630 at quality 88 (about 80-270 KB). A grid of them was over 1 MB on a phone,
most of it pixels nobody sees on a 375 px card. The gallery now also returns `poster_card`, an 800 px WebP
(about a quarter of the bytes), made once from poster.jpg the first time the gallery lists the film and kept next
to it. The page uses it as the default and keeps poster.jpg as the large `srcset` candidate.

How: `card_url()` takes the poster's /media URL, finds the file under the data folder, and writes
`poster_card.webp` with an atomic replace (api/fileio.py) when it is missing or older than the poster. Any
failure (no Pillow codec, odd URL, unreadable file) returns None, and the page falls back to poster.jpg.
"""
from __future__ import annotations

import io
import logging
import re
import threading
from pathlib import Path

from .config import settings
from .fileio import atomic_write_bytes

log = logging.getLogger("dalang.thumbs")
CARD_WIDTH = 800
CARD_QUALITY = 74
CARD_NAME = "poster_card.webp"
_MEDIA = re.compile(r"^/media/([A-Za-z0-9_-]{4,40})/([A-Za-z0-9_./-]+\.(?:jpg|jpeg|png|webp))(?:\?.*)?$")
_lock = threading.Lock()  # two gallery requests at once make one card, not two racing writes


def _make(src: Path, out: Path) -> None:
    from PIL import Image

    with Image.open(src) as opened:
        im = opened.convert("RGB")
    if im.width > CARD_WIDTH:
        im = im.resize((CARD_WIDTH, round(im.height * CARD_WIDTH / im.width)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=CARD_QUALITY, method=4)
    atomic_write_bytes(out, buf.getvalue())


def card_url(poster_url: str | None) -> str | None:
    """The /media URL of the poster's card-size WebP (made on first use), or None when it can't be made."""
    m = _MEDIA.match(poster_url or "")
    if not m:
        return None
    jid, rel = m.groups()
    if ".." in rel:
        return None
    jobs = (settings.data_dir / "jobs").resolve()
    src = (jobs / jid / rel).resolve()
    if jobs not in src.parents or not src.is_file():
        return None
    out = src.parent / CARD_NAME
    try:
        with _lock:
            if not out.is_file() or out.stat().st_mtime < src.stat().st_mtime:
                _make(src, out)
        rel_out = out.relative_to(jobs / jid).as_posix()
        return f"/media/{jid}/{rel_out}?v={int(out.stat().st_mtime)}"
    except Exception as e:  # noqa: BLE001 - a missing card only costs bytes, never the gallery
        log.warning("poster card for %s failed: %s", jid, type(e).__name__)
        return None
