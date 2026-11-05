"""Draw the website's share card and app icons (self-made vector art, no model output, no placeholder art).

    python scripts/make_web_assets.py

Writes web/app/opengraph-image.png + twitter-image.png (1200x630, the link preview on X, WhatsApp and Facebook),
docs/screenshots/poster.jpg (1200x630 share poster: the Kancil sample film's poster frame (live Meta models) from docs/screenshots/kancil-film-poster.jpg
with the tagline band),
web/app/apple-icon.png (180 px) and web/public/icon-192.png, icon-512.png, icon-maskable-512.png (PWA manifest).
The gunungan shape is the same one as web/app/icon.svg.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BG, RED, GOLD, CREAM = (27, 15, 7), (157, 43, 30), (227, 177, 79), (245, 230, 200)
TAGLINE = ("A child tells a story out loud. "
           "Six Meta models perform it as a Javanese shadow-puppet film.")
TAGLINE_LINES = ("A child tells a story out loud.", "Six Meta models perform it as", "a Javanese shadow-puppet film.")
SERIF = ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf",
         "/System/Library/Fonts/Supplemental/Georgia Bold.ttf")
SANS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf")


def font(paths: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def gunungan(draw: ImageDraw.ImageDraw, x: float, y: float, s: float) -> None:
    """The icon.svg gunungan in a 64-unit box at (x, y), scale s per unit."""
    def P(px: float, py: float) -> tuple[float, float]:
        return (x + px * s, y + py * s)
    pts = (_bezier(P(32, 6), P(46, 22), P(52, 34), P(50, 46)) + _bezier(P(50, 46), P(48, 54), P(40, 58), P(32, 58))
           + _bezier(P(32, 58), P(24, 58), P(16, 54), P(14, 46)) + _bezier(P(14, 46), P(12, 34), P(18, 22), P(32, 6)))
    draw.polygon(pts, fill=RED)
    draw.line([*pts, pts[0], pts[1]], fill=GOLD, width=max(2, round(3 * s)), joint="curve")
    w = max(2, round(2.5 * s))
    draw.line([P(32, 16), P(32, 56)], fill=GOLD, width=w)
    draw.line([P(22, 30), P(32, 38), P(42, 30)], fill=GOLD, width=w, joint="curve")
    draw.line([P(20, 42), P(32, 50), P(44, 42)], fill=GOLD, width=w, joint="curve")


def icon(size: int, pad: float = 0.0) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    s = size * (1 - 2 * pad) / 64
    gunungan(d, size * pad, size * pad, s)
    return img


def share_card() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), BG)
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse((-200, -260, 900, 760), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(Image.new("RGB", (w, h), (120, 72, 30)), img, glow)  # blencong lamp light on the kelir
    d = ImageDraw.Draw(img)
    gunungan(d, 760, 70, 7.4)
    d.text((70, 150), "Dalang AI", font=font(SERIF, 104), fill=GOLD)
    d.text((74, 278), "Ceritamu jadi wayang.", font=font(SERIF, 44), fill=CREAM)
    y = 345
    for ln in TAGLINE_LINES:
        d.text((74, y), ln, font=font(SANS, 31), fill=CREAM)
        y += 42
    d.text((74, 540), "Bahasa Indonesia · Basa Jawa · English", font=font(SANS, 26), fill=GOLD)
    return img


def poster_card(src: Path) -> Image.Image:
    """Share poster: the sample film's frame (its old caption band covered) with title + tagline."""
    w, h = 1200, 630
    img = Image.open(src).convert("RGB").resize((w, h))
    band_h = 200
    img = img.convert("RGBA")
    fade = Image.new("RGBA", (w, 40), (12, 6, 2, 0))
    for yy in range(40):  # soft edge above the opaque band
        ImageDraw.Draw(fade).line([(0, yy), (w, yy)], fill=(12, 6, 2, int(255 * yy / 40)))
    img.alpha_composite(fade, (0, h - band_h - 40))
    img.alpha_composite(Image.new("RGBA", (w, band_h), (12, 6, 2, 255)), (0, h - band_h))  # hides the old caption
    d = ImageDraw.Draw(img)
    note = "Contoh cerita · Sample story written for this project, made with the live Meta models"
    nf = font(SANS, 18)
    d.rectangle((16, 14, 16 + d.textlength(note, font=nf) + 16, 44), fill=(12, 6, 2))
    d.text((24, 18), note, font=nf, fill=CREAM)
    d.text((40, h - band_h + 16), "Dalang AI", font=font(SERIF, 52), fill=GOLD)
    y = h - band_h + 86
    for ln in (TAGLINE[:TAGLINE.index("Six")].strip(), TAGLINE[TAGLINE.index("Six"):]):
        d.text((42, y), ln, font=font(SANS, 30), fill=CREAM)
        y += 44
    return img.convert("RGB")


def main() -> None:
    (WEB / "public").mkdir(exist_ok=True)
    card = share_card()
    card.save(WEB / "app" / "opengraph-image.png", optimize=True)
    card.save(WEB / "app" / "twitter-image.png", optimize=True)
    icon(180).save(WEB / "app" / "apple-icon.png", optimize=True)
    icon(192).save(WEB / "public" / "icon-192.png", optimize=True)
    icon(512).save(WEB / "public" / "icon-512.png", optimize=True)
    icon(512, pad=0.12).save(WEB / "public" / "icon-maskable-512.png", optimize=True)  # safe zone for Android masks
    src = ROOT / "docs" / "screenshots" / "kancil-film-poster.jpg"
    if src.exists():
        poster_card(src).save(ROOT / "docs" / "screenshots" / "poster.jpg", quality=90)
    print("wrote share card, poster and icons")


if __name__ == "__main__":
    main()
