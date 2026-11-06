"""The digital kelir. Plays Muse Wonder's keyframe motion plans with SAM-cut puppets over Muse Image
backdrops: lamp flicker, wayang shadows, gunungan transitions, subtitles, title cards. Any aspect ratio."""
from __future__ import annotations

import math
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import gamelan, media

FONT_SANS = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]
FONT_SERIF = ["C:/Windows/Fonts/georgiab.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
ASSET_FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts"


def font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont:
    bundled = sorted(ASSET_FONT.glob("*.ttf")) if ASSET_FONT.exists() else []
    for p in [*map(str, bundled), *(FONT_SERIF if serif else []), *FONT_SANS]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)  # type: ignore[return-value]


def smooth(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ----------------------------------------------------------------------------- assets
@dataclass
class Puppet:
    img: Image.Image  # facing right
    flipped: Image.Image
    shadow: Image.Image
    shadow_flipped: Image.Image


def ref_size(W: int, H: int) -> int:
    """Puppet scale reference: frame height on landscape, a narrower share of width on vertical."""
    return min(H, int(W * 0.9)) if W >= H else int(W * 0.72)


def load_puppet(path: Path, kind: str, S: int) -> Puppet:
    """S = reference size (min(H, 0.9W)); humans ~68% of it, animals ~50%."""
    im = Image.open(path).convert("RGBA")
    target_h = int(S * (0.50 if kind == "animal" else 0.68))
    scale = target_h / im.height
    if im.width * scale > S * 0.78:  # very wide figures (crocodiles, dragons)
        scale = S * 0.78 / im.width
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
    sh = Image.new("RGBA", im.size, (12, 6, 2, 0))
    sh.putalpha(im.split()[-1].point(lambda v: int(v * 0.55)).filter(ImageFilter.GaussianBlur(max(3, S // 80))))
    return Puppet(im, im.transpose(Image.Transpose.FLIP_LEFT_RIGHT), sh, sh.transpose(Image.Transpose.FLIP_LEFT_RIGHT))


def cover(path: Path | Image.Image, W: int, H: int, over: float = 1.0) -> Image.Image:
    im = (Image.open(path) if isinstance(path, Path) else path).convert("RGB")
    tw, th = int(W * over), int(H * over)
    s = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.Resampling.LANCZOS)
    left, top = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((left, top, left + tw, top + th))


def wrap_px(text: str, f: ImageFont.FreeTypeFont, max_w: float, max_lines: int) -> list[str]:
    """Word-wrap by measured pixel width, so captions never run off a phone screen."""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    # no single word alone on the last line ("lapar."): borrow one from the line above when it still fits
    if 1 < len(lines) <= max_lines and " " not in lines[-1] and lines[-2].count(" ") >= 2:
        head, moved = lines[-2].rsplit(" ", 1)
        if d.textlength(f"{moved} {lines[-1]}", font=f) <= max_w:
            lines[-2:] = [head, f"{moved} {lines[-1]}"]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "..."
    return lines


def caption_layer(text: str, W: int, H: int) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vertical = H > W
    f = font(max(18, (W // 22) if vertical else (H // 25)))
    lines = wrap_px(text, f, W * 0.88, 6 if vertical else 3)
    lh = int(f.size * 1.3)
    box_h = lh * len(lines) + 24
    y0 = H - box_h - (int(H * 0.07) if vertical else 14)
    d = ImageDraw.Draw(layer)
    d.rectangle([0, y0 - 12, W, y0 + box_h], fill=(12, 6, 2, 200))
    y = y0
    for ln in lines:
        w = d.textlength(ln, font=f)
        x = (W - w) / 2
        d.text((x + 2, y + 2), ln, font=f, fill=(0, 0, 0, 220))
        d.text((x, y), ln, font=f, fill=(255, 236, 196, 255))
        y += lh
    return layer


def kelir_glow(W: int, H: int) -> Image.Image:
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.42) / (H * 0.75)) ** 2)
    g = np.clip(1 - r, 0, 1) ** 1.6
    arr = np.stack([40 + 200 * g, 18 + 140 * g, 6 + 70 * g, np.full_like(g, 255)], axis=-1).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def vignette(W: int, H: int) -> Image.Image:
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 3] = 20, 8, (np.clip((r - 0.55) * 1.6, 0, 1) * 200).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def card(W: int, H: int, title: str, subtitle: str, gunungan: Image.Image | None, aksara_line: str = "") -> Image.Image:
    """Title / end card. aksara_line: the title in Javanese script (Hanacaraka), drawn above the Latin title with
    Noto Sans Javanese (OFL) and complex shaping, like the aksara on a wayang performance banner."""
    base = kelir_glow(W, H)
    if gunungan is not None:
        g = gunungan.copy()
        g.thumbnail((int(W * 0.42), int(H * 0.50)))
        base.alpha_composite(g, ((W - g.width) // 2, int(H * 0.06)))
    d = ImageDraw.Draw(base)
    ref = min(W, H)
    ft, fs = font(max(26, ref // 14), serif=True), font(max(14, ref // 34))
    y = H * 0.62
    if aksara_line:
        from .. import aksara

        fa = aksara.font(max(20, ref // 20))
        if fa is not None:
            line = aksara_line
            while d.textlength(line, font=fa) > W * 0.86 and " " in line:
                line = line.rsplit(" ", 1)[0]
            w = d.textlength(line, font=fa)
            box = d.textbbox((0, 0), line, font=fa)  # pasangan hang below the line: sit the whole box above the title
            d.text(((W - w) / 2, y - box[3] - ref * 0.02), line, font=fa, fill=(240, 190, 110, 235))
    for txt, f, gap in ((title, ft, 1.18), (subtitle, fs, 1.3)):
        for ln in wrap_px(txt, f, W * 0.86, 3):
            w = d.textlength(ln, font=f)
            d.text(((W - w) / 2 + 2, y + 2), ln, font=f, fill=(0, 0, 0, 230))
            d.text(((W - w) / 2, y), ln, font=f, fill=(255, 214, 140, 255))
            y += f.size * gap
        y += ref * 0.03
    return base


MOOD_TINT = {"night": (0.78, 0.85, 1.05), "tense": (1.05, 0.9, 0.85), "magical": (1.05, 1.0, 1.08),
             "triumphant": (1.08, 1.03, 0.92), "happy": (1.04, 1.02, 0.96), "calm": (1.0, 1.0, 1.0)}
STYLE_TINT = {"classic": (1.04, 0.97, 0.86), "colorful": (1.0, 1.0, 1.0)}


# ----------------------------------------------------------------------------- motion
def pose(track: dict, u: float, t: float, idx: int) -> tuple[float, float, float, str]:
    """Interpolate a Muse Wonder keyframe track at normalised time u; add a living idle motion."""
    kfs = sorted(track["keyframes"], key=lambda k: k["t"])
    if u <= kfs[0]["t"]:
        a = b = kfs[0]
        k = 0.0
    elif u >= kfs[-1]["t"]:
        a = b = kfs[-1]
        k = 0.0
    else:
        for a, b in zip(kfs, kfs[1:], strict=False):
            if a["t"] <= u <= b["t"]:
                break
        k = smooth((u - a["t"]) / max(1e-6, b["t"] - a["t"]))
    x = a["x"] + (b["x"] - a["x"]) * k
    lift = a.get("lift", 0) + (b.get("lift", 0) - a.get("lift", 0)) * k
    ang = a.get("angle", 0) + (b.get("angle", 0) - a.get("angle", 0)) * k
    facing = (b if k > 0.5 else a).get("facing", "right")
    ph = idx * 1.7
    idle = track.get("idle", "sway")
    if idle == "sway":
        ang += 2.6 * math.sin(t * 2.3 + ph)
    elif idle == "bob":
        lift += abs(math.sin(t * 4.0 + ph)) * 0.025
    elif idle == "tremble":
        ang += 1.6 * math.sin(t * 31 + ph)
    if abs(b["x"] - a["x"]) > 0.02 and 0 < k < 1:  # walking gait while travelling
        lift += abs(math.sin(t * 6.0 + ph)) * 0.015
    return x, lift, ang, facing


def _paste(frame: Image.Image, im: Image.Image, x: int, y: int, max_y: int | None = None) -> None:
    """Composite im at (x, y), clipped to the frame and, when max_y is given, to the rows above max_y."""
    left, top = max(0, x), max(0, y)
    right, bottom = min(frame.width, x + im.width), min(frame.height, y + im.height, max_y if max_y is not None else frame.height)
    if right > left and bottom > top:
        frame.alpha_composite(im.crop((left - x, top - y, right - x, bottom - y)), (left, top))


QR_SECONDS = 3.0


def qr_badge(qr_rgb: Image.Image, W: int, H: int, label: str) -> Image.Image:
    """QR code on a cream tile with a short label under it, sized for the corner of the end card."""
    side = int(min(W, H) * 0.24)
    q = qr_rgb.resize((side, side), Image.Resampling.NEAREST).convert("RGBA")
    f = font(max(12, side // 11))
    pad = max(6, side // 20)
    tile = Image.new("RGBA", (side + 2 * pad, side + 2 * pad + int(f.size * 1.5)), (251, 239, 213, 240))
    tile.alpha_composite(q, (pad, pad))
    d = ImageDraw.Draw(tile)
    w = d.textlength(label, font=f)
    d.text(((tile.width - w) / 2, side + pad + 2), label, font=f, fill=(27, 15, 7, 255))
    return tile


# ----------------------------------------------------------------------------- timeline
@dataclass
class Shot:
    duration: float
    bg: Image.Image  # oversized backdrop for camera moves
    plan: dict  # MotionPlan as dict
    mood: str = "calm"
    caption: Image.Image | None = None
    narration_wav: Path | None = None
    cue: dict | None = None  # the Dalang Director's shot: transition, gamelan cue, sound effects

    _ctop: int = field(default=-2, init=False, repr=False, compare=False)  # -2 = not measured yet

    @property
    def caption_top(self) -> int | None:
        """Top row of the caption band. Puppets and their rods stop there, so a rod never runs through the words."""
        if self.caption is None:
            return None
        if self._ctop == -2:
            box = self.caption.getbbox()
            self._ctop = box[1] if box else -1
        return self._ctop if self._ctop >= 0 else None


@dataclass
class Film:
    W: int
    H: int
    style: str = "classic"
    shots: list[Shot] = field(default_factory=list)
    title_card: Image.Image | None = None
    end_card: Image.Image | None = None
    title_len: float = 0.0
    end_len: float = 0.0
    gunungan: Image.Image | None = None
    opening_wav: Path | None = None  # the dalang's opening line, spoken over the title card
    opening_caption: Image.Image | None = None
    scale: str | None = None  # gamelan tuning override (slendro | pelog); None = per mood
    end_qr: Image.Image | None = None  # QR to the app, shown in the last 3 s of the end card (PUBLIC_BASE_URL only)

    @property
    def total(self) -> float:
        return self.title_len + sum(s.duration for s in self.shots) + self.end_len


class Kelir:
    def __init__(self, film: Film, puppets: dict[str, Puppet]):
        self.f, self.p = film, puppets
        self.vig = vignette(film.W, film.H)
        self.black = Image.new("RGBA", (film.W, film.H), (0, 0, 0, 255))
        self.vertical = film.H > film.W
        self.floor = film.H * (0.80 if self.vertical else 0.93)
        self._rot: dict[tuple[str, bool, int], tuple[Image.Image, Image.Image]] = {}

    ANGLE_STEP = 0.2  # degrees; idle sway peaks at about 0.25 deg per frame, so the steps are not visible
    CACHE_MAX = 96

    def _rotated(self, pid: str, p: Puppet, facing: str, ang: float) -> tuple[Image.Image, Image.Image]:
        """Puppet and shadow at this angle, from a small cache (rotation was a third of the frame time)."""
        img, shd = (p.img, p.shadow) if facing != "left" else (p.flipped, p.shadow_flipped)
        q = round(ang / self.ANGLE_STEP)
        if q == 0:
            return img, shd
        key = (pid, facing != "left", q)
        hit = self._rot.get(key)
        if hit is None:
            a = q * self.ANGLE_STEP
            hit = (img.rotate(a, resample=Image.Resampling.BICUBIC, expand=True),
                   shd.rotate(a, resample=Image.Resampling.BILINEAR, expand=True))  # the shadow is soft anyway
            if len(self._rot) >= self.CACHE_MAX:
                self._rot.pop(next(iter(self._rot)))
            self._rot[key] = hit
        return hit

    def frame(self, T: float) -> Image.Image:
        f = self.f
        if T < f.title_len and f.title_card is not None:
            fr = self._fade(f.title_card, min(1.0, T / 0.8))
            if f.opening_caption is not None and T > 0.9:
                fr.alpha_composite(f.opening_caption)
            return fr
        t = T - f.title_len
        for i, sh in enumerate(f.shots):
            if t < sh.duration:
                fr = self.shot_frame(sh, t)
                self._gunungan(fr, i, t, sh.duration)
                return fr
            t -= sh.duration
        if f.end_card is not None:
            card_im = f.end_card
            if f.end_qr is not None and t >= f.end_len - QR_SECONDS:
                card_im = card_im.copy()
                m = int(min(f.W, f.H) * 0.04)
                card_im.alpha_composite(f.end_qr, (f.W - f.end_qr.width - m, f.H - f.end_qr.height - m))
            return self._fade(card_im, min(1.0, max(0.0, (f.end_len - t) / 0.8)))
        return self.black.copy()

    def _fade(self, im: Image.Image, k: float) -> Image.Image:
        return im.copy() if k >= 1 else Image.blend(self.black, im, k)

    def shot_frame(self, sh: Shot, t: float) -> Image.Image:
        W, H = self.f.W, self.f.H
        u = t / max(sh.duration, 0.1)
        cam = sh.plan.get("camera", {})
        zoom = cam.get("zoom_from", 1.0) + (cam.get("zoom_to", 1.06) - cam.get("zoom_from", 1.0)) * smooth(u)
        bw, bh = sh.bg.size
        cw, ch = int(bw / zoom), int(bh / zoom)
        cx = (bw - cw) / 2 * (1 + cam.get("pan_x", 0.0) * (2 * u - 1) * 0.9)
        cy = (bh - ch) / 2 * (1 + cam.get("pan_y", 0.0) * (2 * u - 1) * 0.9)
        cx, cy = min(max(0, cx), bw - cw), min(max(0, cy), bh - ch)
        bg = sh.bg.crop((int(cx), int(cy), int(cx) + cw, int(cy) + ch)).resize((W, H), Image.Resampling.BILINEAR)
        fl = sh.plan.get("lamp_flicker", 0.4)
        flick = 1.0 - 0.02 * fl + 0.035 * fl * math.sin(t * 3.1 + math.sin(t * 1.3) * 2) + 0.012 * fl * math.sin(t * 23)
        mr, mg, mb = MOOD_TINT.get(sh.mood, (1, 1, 1))
        sr, sg, sb = STYLE_TINT.get(self.f.style, (1, 1, 1))
        lut = []
        for c in (mr * sr, mg * sg, mb * sb):
            lut += [min(255, int(v * flick * c)) for v in range(256)]
        fr = bg.point(lut).convert("RGBA")
        S = ref_size(W, H)
        a = min(1.0, max(0.0, (t - 0.3) / 0.5)) if sh.caption is not None else 0.0
        clip = sh.caption_top if a > 0 else None
        for idx, tr in enumerate(sh.plan.get("puppets", [])):
            p = self.p.get(tr["id"])
            if p is None:
                continue
            x, lift, ang, facing = pose(tr, u, t, idx)
            if self.vertical:
                x = 0.5 + (x - 0.5) * 0.62
            img, shd = self._rotated(tr["id"], p, facing, ang)
            px = int(x * W - img.width / 2)
            py = int(self.floor - lift * S - img.height)
            _paste(fr, shd, px - S // 60, py - S // 90, clip)  # the blencong casts a soft shadow up-left
            _paste(fr, img, px, py, clip)
        fr.alpha_composite(self.vig)
        if sh.caption is not None:
            if a >= 1:
                fr.alpha_composite(sh.caption)
            elif a > 0:
                fr.alpha_composite(Image.blend(Image.new("RGBA", sh.caption.size, (0, 0, 0, 0)), sh.caption, a))
        return fr

    def _gunungan(self, fr: Image.Image, i: int, t: float, dur: float) -> None:
        """The gunungan sweeps across every cut, as the dalang does between scenes."""
        g = self.f.gunungan
        if g is None:
            return
        half = 0.55
        if t < half and i > 0:
            k = 0.5 + 0.5 * (t / half)
            kind = (self.f.shots[i - 1].cue or {}).get("transition", "gunungan_sweep")
        elif dur - t < half and i < len(self.f.shots) - 1:
            k = 0.5 * (1 - (dur - t) / half)
            kind = (self.f.shots[i].cue or {}).get("transition", "gunungan_sweep")
        else:
            return
        W, H = self.f.W, self.f.H
        if kind == "cut":
            return
        if kind == "fade":  # dip to black and back
            a = int(255 * (1 - abs(k - 0.5) * 2))
            fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, a)))
            return
        if kind == "gunungan_rise":  # the kayon rises in the centre, fills the screen, then sinks away
            y = int(H - k * 2 * (H + g.height) / 2) if k <= 0.5 else int((H - g.height) / 2 + (k - 0.5) * 2 * (H + g.height) / 2)
            _paste(fr, g, int((W - g.width) / 2), y)
            return
        x = int(W + g.width * 0.1 - k * (W + g.width * 1.2))
        _paste(fr, g, x, int((H - g.height) / 2))


def encode(kelir: Kelir, out: Path, fps: int, progress: Callable[[float], None] | None = None,
           poster: Path | None = None) -> Path:
    W, H = kelir.f.W, kelir.f.H
    n = max(1, int(kelir.f.total * fps))
    with media.staged(out) as dst:
        return _encode(kelir, out, dst, fps, n, W, H, progress, poster)


def _encode(kelir: Kelir, out: Path, dst: Path, fps: int, n: int, W: int, H: int,
            progress: Callable[[float], None] | None, poster: Path | None) -> Path:
    cmd = [media.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None and proc.stderr is not None
    try:
        for k in range(n):
            fr = kelir.frame(k / fps).convert("RGB")
            proc.stdin.write(fr.tobytes())
            if poster is not None and k == min(n - 1, int(n * 0.5)):
                fr.save(poster, quality=88)
            if progress and k % fps == 0:
                progress(k / n)
    finally:
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="ignore")
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg encode failed: {err[-600:]}")
    return out


def soundtrack(film: Film, out_wav: Path) -> Path:
    """Narration, the gong and bonang cues on the title and end cards (made in code), and the gamelan bed under the
    scenes (music_bed: the Kraton recording, CC BY 4.0, or the code-made ensemble)."""
    sr = media.SR
    total = np.zeros(int(film.total * sr) + sr, np.float32)
    voice = np.zeros_like(total)  # narration only, used to duck the music bed

    def add(sig: np.ndarray, at: float, gain: float = 1.0) -> None:
        i = int(at * sr)
        j = min(len(total), i + len(sig))
        if j > i:
            total[i:j] += sig[: j - i] * gain

    if film.opening_wav:
        add(media.read_wav(film.opening_wav), 1.0)
    if film.title_len:
        add(media.gong(4.0, 70.0), 0.15)
        for n, note in enumerate([0, 2, 4, 3, 1, 2]):
            add(media.bonang(media.SLENDRO[note]), 0.6 + n * 0.42)
    t = film.title_len
    for i, sh in enumerate(film.shots):
        cue = sh.cue or {}
        kind = cue.get("gamelan")
        if kind and kind != "none":  # the Dalang Director's gamelan cue for this scene
            add(gamelan.cue(kind, film.scale or gamelan.style_for(sh.mood).scale), t, 0.9)
        elif i > 0:
            add(media.gong(3.0, 98.0), t, 0.7)
        for fx in cue.get("sfx", []):
            add(gamelan.sfx(fx["kind"], seed=i), t + float(fx["t"]) * max(0.5, sh.duration - 0.8), 0.8)
        if sh.narration_wav:
            speech = media.read_wav(sh.narration_wav)
            add(speech, t + 0.6)
            i = int((t + 0.6) * sr)
            j = min(len(voice), i + len(speech))
            if j > i:
                voice[i:j] += speech[: j - i]
        t += sh.duration
    if film.end_len:
        add(media.gong(4.0, 70.0), t)
        for n, note in enumerate([2, 1, 0]):
            add(media.bonang(media.SLENDRO[note]), t + 0.5 + n * 0.5)
    total += music_bed(film, voice)
    peak = float(np.max(np.abs(total))) or 1.0
    media.write_wav(out_wav, total * (0.9 / peak if peak > 0.9 else 1.0))
    return out_wav


def music_bed(film: Film, voice: np.ndarray, beat: float = 0.72, level: float = 1.0, ducked: float = 0.3) -> np.ndarray:
    """Gamelan under the scenes (api/pipeline/gamelan.py), cross-faded at the cuts and ducked while the dalang
    speaks. By default a real Kraton recording (calm or lively excerpt per scene mood, CC BY 4.0); with
    GAMELAN_SOURCE=procedural each scene gets its mood's code-made tuning, irama and kendang pattern."""
    sr = media.SR
    bed = np.zeros_like(voice)
    start, end = film.title_len, film.total - film.end_len
    t = start
    xf = int(0.6 * sr)
    for i, sh in enumerate(film.shots):
        if gamelan.source() == "recording":
            seg = gamelan.recorded(sh.mood, sh.duration + 0.6, offset=t)
        else:
            seg = gamelan.render(sh.mood, sh.duration + 0.6, scale=film.scale, seed=i)
        env = np.ones(len(seg), np.float32)
        r = min(xf, len(seg) // 2)
        env[:r] = np.linspace(0, 1, r)
        env[-r:] = np.linspace(1, 0, r)
        a = int(t * sr)
        b = min(len(bed), a + len(seg))
        if b > a:
            bed[a:b] += (seg * env)[: b - a] * 0.55
        t += sh.duration
    # ducking envelope from the narration loudness, smoothed over ~0.25 s
    win = int(0.25 * sr)
    duck = np.convolve(np.abs(voice), np.ones(win) / win, mode="same")
    talking = np.clip(duck / 0.02, 0.0, 1.0)
    gain = level - (level - ducked) * talking
    fade = np.ones_like(bed)
    a, b = int(start * sr), int(end * sr)
    ramp = int(0.8 * sr)
    fade[:a] = 0.0
    fade[b:] = 0.0
    if b - a > 2 * ramp:
        fade[a:a + ramp] = np.linspace(0, 1, ramp)
        fade[b - ramp:b] = np.linspace(1, 0, ramp)
    return (bed * gain * fade).astype(np.float32)


def poster(kelir: Kelir, title: str, out: Path, size: tuple[int, int] = (1200, 630)) -> Path:
    """Share card (Open Graph size): the first scene with its puppets, a gold title band and the gunungan."""
    shot = kelir.f.shots[0]
    frame = kelir.shot_frame(Shot(duration=shot.duration, bg=shot.bg, plan=shot.plan, mood=shot.mood), shot.duration * 0.5)
    W, H = size
    im = cover(frame.convert("RGB"), W, H).convert("RGBA")
    band = Image.new("RGBA", (W, int(H * 0.26)), (12, 6, 2, 190))
    im.alpha_composite(band, (0, H - band.height))
    if kelir.f.gunungan is not None:
        g = kelir.f.gunungan.copy()
        g.thumbnail((int(W * 0.16), int(H * 0.5)))
        im.alpha_composite(g, (W - g.width - 24, 20))
    d = ImageDraw.Draw(im)
    fs = font(24)
    # the title on one line, shrinking from 54 px; a long one (a remix "· told by ...") takes two smaller lines so it
    # never runs into the tagline at the bottom of the band
    fsize, lines = 54, [title]
    for fsize in range(54, 33, -4):
        ft = font(fsize, serif=True)
        if d.textlength(title, font=ft) <= W * 0.85:
            break
    else:
        fsize = int(54 * (H / 630) * 0.7)
        ft = font(fsize, serif=True)
        lines = wrap_px(title, ft, W * 0.85, 2)
    step = int(fsize * 1.15)
    y = H - band.height + max(8, (band.height - 48 - step * len(lines)) // 2)
    for ln in lines:
        d.text((40 + 2, y + 2), ln, font=ft, fill=(0, 0, 0, 230))
        d.text((40, y), ln, font=ft, fill=(255, 214, 140, 255))
        y += step
    d.text((40, H - 40), "Dalang AI \u00b7 a wayang film from a child's story", font=fs, fill=(251, 239, 213, 230))
    im.convert("RGB").save(out, quality=90)
    return out


def _ts(t: float) -> str:
    h, rem = divmod(max(0.0, t), 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"


def captions_vtt(film: Film, opening: str, lines: list[str], out: Path) -> Path:
    """WebVTT captions matching the burned-in subtitles, for screen readers and the <track> element."""
    cues = []
    if opening and film.opening_wav:
        cues.append((1.0, max(1.5, film.title_len - 0.2), opening))
    t = film.title_len
    for sh, text in zip(film.shots, lines, strict=False):
        cues.append((t + 0.6, t + sh.duration - 0.2, text))
        t += sh.duration
    body = "WEBVTT\n\n" + "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues, 1))
    out.write_text(body, encoding="utf-8")
    return out
