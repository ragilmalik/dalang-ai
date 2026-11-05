"""QR codes for the app's public link (landing page, share card, the film's end card, README, demo video).

PUBLIC_BASE_URL is the deployed website (e.g. https://dalang-ai.vercel.app). Until it is set, the website's QR codes
point at the address the visitor's browser is already using (so a classroom on one Wi-Fi network can scan it), and
no QR is printed into films or the submission kit: there is never a QR to a made-up address.
"""
from __future__ import annotations

import io
from pathlib import Path

import qrcode
from PIL import Image

from .config import settings


def base_url(fallback: str = "") -> str:
    """PUBLIC_BASE_URL, else `fallback` (the address the request came in on), else ""."""
    return settings.public_base_url or fallback.rstrip("/")


def is_placeholder() -> bool:
    """True until PUBLIC_BASE_URL is set (kept under this name for older callers): there is no public link yet."""
    return not settings.public_base_url


def app_url(path: str = "", fallback: str = "") -> str:
    path = path if path.startswith("/") or not path else "/" + path
    return base_url(fallback) + path


def image(data: str, box: int = 10, dark: tuple[int, int, int] = (27, 15, 7),
          light: tuple[int, int, int] = (251, 239, 213)) -> Image.Image:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box, border=2)
    q.add_data(data)
    q.make(fit=True)
    return q.make_image(fill_color=dark, back_color=light).get_image().convert("RGB")


def png_bytes(data: str, box: int = 10) -> bytes:
    buf = io.BytesIO()
    image(data, box).save(buf, "PNG")
    return buf.getvalue()


def save(data: str, out: Path, box: int = 10) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    image(data, box).save(out)
    return out
