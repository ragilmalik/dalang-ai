"""api/thumbs.py: card-size gallery posters (800 px WebP, made once, safe on bad input)."""
import os
import time

from PIL import Image

from api import thumbs
from api.config import settings


def _poster(jid: str, w: int = 1200, h: int = 630):
    d = settings.data_dir / "jobs" / jid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "poster.jpg"
    Image.new("RGB", (w, h), (120, 60, 20)).save(p, quality=88)
    return p


def test_card_is_made_once_and_smaller():
    p = _poster("thumbA1")
    url = thumbs.card_url("/media/thumbA1/poster.jpg?v=1")
    assert url and url.startswith("/media/thumbA1/poster_card.webp?v=")
    card = p.parent / thumbs.CARD_NAME
    with Image.open(card) as im:
        assert im.format == "WEBP" and im.width == thumbs.CARD_WIDTH and im.height == 420
    first = card.stat().st_mtime_ns
    assert thumbs.card_url("/media/thumbA1/poster.jpg") == url  # cached: not rewritten
    assert card.stat().st_mtime_ns == first


def test_card_is_remade_when_the_poster_changes():
    p = _poster("thumbB2")
    thumbs.card_url("/media/thumbB2/poster.jpg")
    card = p.parent / thumbs.CARD_NAME
    old = time.time() - 100
    os.utime(card, (old, old))  # card now older than the poster
    thumbs.card_url("/media/thumbB2/poster.jpg")
    assert card.stat().st_mtime > old + 50


def test_small_poster_is_not_upscaled():
    _poster("thumbC3", 400, 210)
    thumbs.card_url("/media/thumbC3/poster.jpg")
    with Image.open(settings.data_dir / "jobs" / "thumbC3" / thumbs.CARD_NAME) as im:
        assert im.width == 400


def test_bad_input_gives_none():
    assert thumbs.card_url(None) is None
    assert thumbs.card_url("") is None
    assert thumbs.card_url("https://evil.example/x.jpg") is None
    assert thumbs.card_url("/media/thumbX9/../../etc/passwd.jpg") is None
    assert thumbs.card_url("/media/nojob99/poster.jpg") is None  # file missing


def test_broken_poster_gives_none(caplog):
    d = settings.data_dir / "jobs" / "thumbD4"
    d.mkdir(parents=True, exist_ok=True)
    (d / "poster.jpg").write_bytes(b"not a jpeg")
    assert thumbs.card_url("/media/thumbD4/poster.jpg") is None
    assert not (d / thumbs.CARD_NAME).exists()


def test_gallery_returns_poster_card():
    from fastapi.testclient import TestClient

    from api import main

    with TestClient(main.app) as c:
        for f in c.get("/api/gallery").json():
            assert "poster_card" in f
