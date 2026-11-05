"""Procedural gamelan, rendered offline with numpy (no samples, no music licence).

A small Javanese ensemble in code: saron (balungan), bonang (kettle gongs), kenong, kempul, kethuk, gong ageng and
kendang (dhung / tak / ket strokes), on the two Javanese tunings:
  * slendro: five near-equal steps (about 240 cents), here pathet manyura
  * pelog:   seven unequal steps (an approximate pelog barang/nem set, cents 0 120 270 540 670 785 950)
Real gamelan sets are each tuned differently; these are reasonable textbook approximations, stated as such.

Each mood picks a tuning, a tempo (irama), a balungan line and a kendang pattern, and the colotomic instruments mark
the gongan (kenong every 4 beats, kempul between, gong ageng at the end of each 16-beat gongan), as in a lancaran /
ladrang skeleton. The Dalang Director's cues (gong, kempul, kendang_rush, bonang_run, suwuk) and sound effects
(keprak, cempala, wind, water, birds) are rendered here too.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

SR = 24000

SLENDRO_CENTS = [0, 240, 480, 720, 960]
PELOG_CENTS = [0, 120, 270, 540, 670, 785, 950]
BASE_HZ = 262.0  # around C4; gamelan pitch differs per set


def scale_hz(scale: str) -> list[float]:
    cents = SLENDRO_CENTS if scale == "slendro" else PELOG_CENTS
    return [BASE_HZ * 2 ** (c / 1200) for c in cents]


@dataclass
class Style:
    scale: str  # slendro | pelog
    pathet: str
    tempo_bpm: int
    balungan: list[int]  # degrees into the scale, one per beat, 0 = rest
    kendang: str  # one character per half-beat: D dhung, t tak, k ket, . rest
    pattern: str  # name of the kendang pattern
    bonang: bool = True


MOODS: dict[str, Style] = {
    "calm": Style("slendro", "manyura", 66, [3, 2, 3, 1, 3, 2, 1, 6, 2, 1, 2, 6, 3, 5, 3, 2],
                  "D...t...D.t.D...", "ladrang irama tanggung (kendang kalih, gentle)"),
    "happy": Style("pelog", "barang", 96, [2, 3, 2, 7, 2, 3, 5, 6, 5, 3, 2, 3, 5, 6, 7, 6],
                   "D.t.D.tkD.t.DttD", "lancaran (kendang ciblon, lively)"),
    "tense": Style("slendro", "sanga", 120, [5, 6, 5, 3, 5, 6, 5, 3, 2, 1, 2, 3, 5, 3, 2, 1],
                   "DtDtkDtDDtktDDtD", "srepegan (fast, for conflict)", bonang=False),
    "sad": Style("pelog", "nem", 56, [1, 2, 3, 2, 1, 6, 5, 6, 1, 2, 3, 2, 6, 5, 3, 5],
                 "D.......t...D...", "ketawang (slow, irama wilet)"),
    "magical": Style("pelog", "lima", 72, [1, 2, 4, 5, 4, 2, 1, 2, 5, 4, 2, 1, 2, 4, 5, 1],
                     "D...k...D.k.t...", "ayak-ayakan (floating)"),
    "night": Style("slendro", "sanga", 60, [2, 1, 6, 5, 2, 1, 6, 5, 3, 2, 1, 6, 2, 1, 6, 5],
                   "D.......D...t...", "ketawang (night)"),
    "triumphant": Style("slendro", "manyura", 104, [6, 5, 3, 2, 6, 5, 3, 2, 3, 5, 6, 1, 6, 5, 3, 2],
                        "DtD.DtD.DtDkDDtD", "lancaran (kendang bem, triumphant)"),
}
MOOD_NAMES = sorted(MOODS)


def style_for(mood: str, scale: str | None = None) -> Style:
    st = MOODS.get(mood, MOODS["calm"])
    if scale and scale != st.scale:
        n = 5 if scale == "slendro" else 7
        st = Style(scale, "manyura" if scale == "slendro" else "barang", st.tempo_bpm,
                   [((d - 1) % n) + 1 if d else 0 for d in st.balungan], st.kendang, st.pattern, st.bonang)
    return st


# --------------------------------------------------------------------------- instruments
def _t(seconds: float) -> np.ndarray:
    return np.arange(int(SR * seconds)) / SR


def metal(freq: float, seconds: float, partials: list[tuple[float, float]], decay: float, gain: float) -> np.ndarray:
    t = _t(seconds)
    s = sum(a * np.sin(2 * np.pi * freq * r * t) for r, a in partials)
    env = np.exp(-t * decay) * (1 - np.exp(-t * 400))
    return (s * env * gain).astype(np.float32)


def saron(freq: float) -> np.ndarray:
    return metal(freq, 1.2, [(1.0, 1.0), (2.76, 0.25), (5.4, 0.08)], 3.2, 0.10)


def bonang(freq: float) -> np.ndarray:
    return metal(freq, 0.8, [(1.0, 1.0), (1.51, 0.2), (2.01, 0.35)], 5.0, 0.07)


def kenong(freq: float) -> np.ndarray:
    return metal(freq, 2.0, [(1.0, 1.0), (1.003, 0.7), (2.0, 0.15)], 1.6, 0.09)


def kempul(freq: float) -> np.ndarray:
    return metal(freq, 2.5, [(1.0, 1.0), (1.004, 0.8), (2.3, 0.2)], 1.3, 0.11)


def kethuk(freq: float) -> np.ndarray:
    return metal(freq, 0.35, [(1.0, 1.0), (2.2, 0.2)], 14.0, 0.07)


def gong(seconds: float = 4.0, base: float = 65.0) -> np.ndarray:
    t = _t(seconds)
    s = sum(a * np.sin(2 * np.pi * base * r * t) for r, a in [(1.0, 1.0), (1.006, 0.7), (2.76, 0.35), (5.4, 0.12)])
    env = np.exp(-t * 0.9) * (1 - np.exp(-t * 50))
    return (s * env * 0.24).astype(np.float32)


def _noise(seconds: float, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(int(SR * seconds)).astype(np.float32)


def _lowpass(x: np.ndarray, k: int) -> np.ndarray:
    return np.convolve(x, np.ones(k) / k, mode="same").astype(np.float32)


def kendang(stroke: str, seed: int = 0) -> np.ndarray:
    """D: dhung (low membrane, pitch drops), t: tak (dry slap), k: ket (short high slap)."""
    if stroke == "D":
        t = _t(0.45)
        f = 95 + 60 * np.exp(-t * 25)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
        return (s * 0.30).astype(np.float32)
    dur, hp = (0.12, 3) if stroke == "t" else (0.07, 2)
    n = _noise(dur, seed)
    n = n - _lowpass(n, hp * 8)
    return (n * np.exp(-_t(dur) * (55 if stroke == "t" else 80)) * (0.16 if stroke == "t" else 0.11)).astype(np.float32)


# --------------------------------------------------------------------------- sound effects (Director cues)
def sfx(kind: str, seed: int = 0) -> np.ndarray:
    if kind == "keprak":  # the dalang's metal plates against the puppet chest: a bright rattle
        out = np.zeros(int(SR * 0.5), np.float32)
        for i, at in enumerate((0.0, 0.07, 0.13)):
            n = _noise(0.09, seed + i)
            n = (n - _lowpass(n, 6)) * np.exp(-_t(0.09) * 45) * 0.2
            out[int(at * SR): int(at * SR) + len(n)] += n
        return out
    if kind == "cempala":  # wooden knocker on the puppet box: one low woody knock
        t = _t(0.25)
        return (np.sin(2 * np.pi * 180 * t) * np.exp(-t * 40) * 0.35 + _noise(0.25, seed) * np.exp(-t * 90) * 0.05
                ).astype(np.float32)
    if kind == "gong":
        return gong(3.0, 70.0)
    if kind == "wind":
        n = _lowpass(_noise(2.5, seed), 60)
        swell = np.sin(np.linspace(0, math.pi, len(n)))
        return (n * swell * 1.2).astype(np.float32)
    if kind == "water":
        n = _lowpass(_noise(2.0, seed), 12)
        bub = 0.6 + 0.4 * np.sin(2 * np.pi * 7 * _t(2.0))
        return (n * bub * np.sin(np.linspace(0, math.pi, len(n))) * 0.6).astype(np.float32)
    if kind == "birds":
        out = np.zeros(int(SR * 1.6), np.float32)
        for i, at in enumerate((0.0, 0.35, 0.9)):
            t = _t(0.18)
            f = 2600 + 900 * np.sin(np.linspace(0, math.pi, len(t))) + 200 * i
            c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.linspace(0, math.pi, len(t))) * 0.05
            out[int(at * SR): int(at * SR) + len(c)] += c.astype(np.float32)
        return out
    return np.zeros(1, np.float32)


def cue(kind: str, scale: str = "slendro") -> np.ndarray:
    """Director gamelan cues at a scene start."""
    hz = scale_hz(scale)
    if kind == "gong":
        return gong(4.0, 65.0)
    if kind == "kempul":
        return kempul(hz[0] / 2)
    if kind == "kendang_rush":
        out = np.zeros(int(SR * 1.4), np.float32)
        for i, s in enumerate("DtDtkDtkDD"):
            k = kendang(s, i)
            at = int(i * 0.11 * SR)
            out[at: at + len(k)] += k[: len(out) - at]
        return out
    if kind == "bonang_run":
        out = np.zeros(int(SR * 1.6), np.float32)
        for i, f in enumerate(hz + [hz[0] * 2]):
            b = bonang(f)
            at = int(i * 0.12 * SR)
            out[at: at + len(b)] += b[: len(out) - at]
        return out
    if kind == "suwuk":  # the closing: slowing kenong strokes into the great gong
        out = np.zeros(int(SR * 5.0), np.float32)
        for i, sec in enumerate((0.0, 0.7, 1.6)):
            k = kenong(hz[(2 - i) % len(hz)])
            out[int(sec * SR): int(sec * SR) + len(k)] += k
        g = gong(3.0, 62.0)
        out[int(2.0 * SR): int(2.0 * SR) + len(g)] += g
        return out
    return np.zeros(1, np.float32)


# --------------------------------------------------------------------------- the ensemble
def render(mood: str, seconds: float, scale: str | None = None, seed: int = 0) -> np.ndarray:
    """`seconds` of gamelan for a mood: balungan on saron, bonang anticipation, colotomic kenong/kempul/kethuk/gong,
    and the mood's kendang pattern. Deterministic for a given seed."""
    st = style_for(mood, scale)
    hz = scale_hz(st.scale)
    beat = 60.0 / st.tempo_bpm
    out = np.zeros(int(SR * seconds) + SR * 4, np.float32)

    def put(sig: np.ndarray, at: float) -> None:
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        if j > i:
            out[i:j] += sig[: j - i]

    n_beats = int(seconds / beat)
    for b in range(n_beats):
        at = b * beat
        deg = st.balungan[b % len(st.balungan)]
        if deg:
            f = hz[(deg - 1) % len(hz)]
            put(saron(f), at)
            if st.bonang and b % 2 == 1:  # bonang anticipates the next balungan note on the off-beats
                nxt = st.balungan[(b + 1) % len(st.balungan)] or deg
                put(bonang(hz[(nxt - 1) % len(hz)] * 2), at + beat / 2)
        pos = b % 16
        if pos % 4 == 3:
            put(kenong(hz[(deg - 1) % len(hz)] if deg else hz[0]), at)
        elif pos % 4 == 1:
            put(kethuk(hz[1]), at)
        if pos in (5, 9, 13):
            put(kempul(hz[((deg or 1) - 1) % len(hz)] / 2), at)
        if pos == 15:
            put(gong(3.5, 62.0) * 0.8, at)
        for h, s in enumerate(st.kendang[(pos % 8) * 2:(pos % 8) * 2 + 2]):
            if s != ".":
                put(kendang(s, seed + b * 2 + h), at + h * beat / 2)
    out = out[: int(SR * seconds)]
    peak = float(np.max(np.abs(out))) or 1.0
    return (out * min(1.0, 0.5 / peak)).astype(np.float32)


def summary(moods: list[str], scale: str | None = None) -> dict:
    """What the film's score is, for the job state (`score`)."""
    main = style_for(moods[0] if moods else "calm", scale)
    return {"scale": main.scale, "pathet": main.pathet, "tempo_bpm": main.tempo_bpm, "pattern": main.pattern,
            "moods": moods, "procedural": True, "styles": {m: asdict(style_for(m, scale)) for m in dict.fromkeys(moods)}}


def wav_bytes(samples: np.ndarray) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()
