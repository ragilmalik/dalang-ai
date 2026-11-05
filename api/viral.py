"""Shareables per film: a WhatsApp-ready sticker pack of the film's own puppets and a looping GIF.

Stickers follow WhatsApp's sticker rules: 512x512 WebP, transparent background, under 100 KB each, with a 96x96
PNG tray icon; a pack needs at least 3 stickers, so the gunungan and a title sticker fill a small cast. Each sticker
gets the white die-cut outline stickers usually have. The GIF is a short loop from the finished film (ffmpeg
two-pass palette), at most 480 px wide. Both are made once on first request and cached in the film's folder.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .jobs import Job
from .pipeline import engine, media

SIZE, MARGIN, OUTLINE = 512, 16, 8
MAX_BYTES = 100_000
GIF_SECONDS, GIF_WIDTH, GIF_FPS = 3.0, 480, 10


class NotReady(RuntimeError):
    pass


def _diecut(im: Image.Image) -> Image.Image:
    """Fit a cut-out puppet into 512x512 with a margin and a white outline around its silhouette."""
    im = im.convert("RGBA")
    box = SIZE - 2 * (MARGIN + OUTLINE)
    im.thumbnail((box, box), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    x, y = (SIZE - im.width) // 2, (SIZE - im.height) // 2
    alpha = Image.new("L", (SIZE, SIZE), 0)
    alpha.paste(im.split()[-1], (x, y))
    halo = alpha.point(lambda v: 255 if v > 24 else 0).filter(ImageFilter.MaxFilter(OUTLINE * 2 + 1))
    canvas.paste(Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255)), (0, 0), halo.filter(ImageFilter.GaussianBlur(1)))
    canvas.alpha_composite(im, (x, y))
    return canvas


def _title_sticker(title: str, gunungan: Path | None) -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([MARGIN, SIZE * 0.28, SIZE - MARGIN, SIZE * 0.72], radius=40, fill=(60, 30, 14, 255),
                        outline=(255, 255, 255, 255), width=OUTLINE)
    f = engine.font(44, serif=True)
    lines = engine.wrap_px(title, f, SIZE - 4 * MARGIN - 20, 2)
    y = SIZE / 2 - len(lines) * f.size * 0.6
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((SIZE - w) / 2, y), ln, font=f, fill=(255, 214, 140, 255))
        y += f.size * 1.15
    return canvas


def _webp(im: Image.Image, out: Path) -> Path:
    for q in (90, 80, 70, 60, 50, 40):
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=6)
        if buf.tell() <= MAX_BYTES:
            break
    out.write_bytes(buf.getvalue())
    return out


def stickers(job: Job) -> list[dict]:
    """Make (once) and list the film's stickers."""
    puppets = job.dir / "puppets"
    cast = job.s.get("cast") or []
    if not cast or not puppets.is_dir():
        raise NotReady("The puppets are not carved yet.")
    sdir = job.dir / "stickers"
    sdir.mkdir(exist_ok=True)
    items = [(c["id"], c["name"], puppets / f"{c['id']}.png") for c in cast]
    if len(items) < 3 and (puppets / "gunungan.png").exists():
        items.append(("gunungan", "Gunungan", puppets / "gunungan.png"))
    out = []
    for sid, name, src in items:
        if not src.exists():
            continue
        dst = sdir / f"{sid}.webp"
        if not dst.exists():
            _webp(_diecut(Image.open(src)), dst)
        out.append({"id": sid, "name": name, "url": job.url(dst), "w": SIZE, "h": SIZE})
    if len(out) < 3:
        dst = sdir / "title.webp"
        if not dst.exists():
            _webp(_title_sticker(job.s.get("title") or "Dalang AI", None), dst)
        out.append({"id": "title", "name": job.s.get("title") or "Dalang AI", "url": job.url(dst), "w": SIZE, "h": SIZE})
    tray = sdir / "tray.png"
    if not tray.exists():
        first = Image.open(sdir / f"{out[0]['id']}.webp").convert("RGBA")
        first.resize((96, 96), Image.Resampling.LANCZOS).save(tray, optimize=True)
    return out


README = """Dalang AI sticker pack: {title}

{n} stickers (512x512 WebP, transparent) of the puppets from this film, plus tray.png (96x96).
WhatsApp: open a sticker-maker app (for example "Sticker Maker" on Android or iPhone), make a new pack,
add these .webp files and tray.png as the pack icon, then "Add to WhatsApp".
Made with Dalang AI: puppets drawn by Meta Muse Image and cut out by SAM 3.1.
"""


def sticker_zip(job: Job) -> Path:
    items = stickers(job)
    out = job.dir / "stickers" / "dalang-stickers.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for it in items:
            z.write(job.dir / "stickers" / f"{it['id']}.webp", f"{it['id']}.webp")
        z.write(job.dir / "stickers" / "tray.png", "tray.png")
        z.writestr("README.txt", README.format(title=job.s.get("title") or "Dalang AI", n=len(items)))
    return out


def gif_loop(job: Job) -> Path:
    """A short looping GIF from the first scene of the finished film (after the title card)."""
    video = job.dir / "dalang_landscape.mp4"
    if not video.exists():
        raise NotReady("The film is not finished yet.")
    out = job.dir / "loop.gif"
    if out.exists() and out.stat().st_mtime >= video.stat().st_mtime:
        return out
    dur = float(job.s.get("duration_s") or 0)
    start = min(6.0, max(0.0, dur * 0.25)) if dur > GIF_SECONDS + 1 else 0.0  # into the first scene, past the title
    vf = f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos"
    media.run(["-ss", f"{start:.2f}", "-t", str(GIF_SECONDS), "-i", str(video), "-vf",
               f"{vf},split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
               "-loop", "0", str(out)])
    return out
