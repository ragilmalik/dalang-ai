"""Latin -> Javanese script (aksara Jawa / Hanacaraka, Unicode U+A980-U+A9DF) for film titles.

A rule-based syllable transliterator, good for titles and names, not a scholarly one:
  * a vowel right after u/o or i gets the glide wa / ya (buaya -> bu-wa-ya), as Javanese spelling does
  * consonants -> aksara nglegena (ng, ny, dh, th as single letters); vowels -> sandhangan
    (i wulu, u suku, e pepet, é/è taling, o taling-tarung); a vowel with no consonant is carried by ha (ꦲ)
  * a consonant with no vowel: final ng -> cecak, r -> layar, h -> wignyan; any other -> pangkon (virama),
    which a shaping engine (HarfBuzz/raqm) draws as a pasangan before the next consonant; r and y right after a
    consonant become cakra and pengkal
  * digits -> Javanese digits; , . -> pada lingsa / pada lungsi; anything else (emoji, quotes) is dropped
Ambiguities are resolved the common modern way (plain "e" -> pepet). Rendered with Noto Sans Javanese (SIL OFL 1.1,
content/fonts/, https://github.com/notofonts/javanese).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

FONT = Path(__file__).resolve().parent.parent / "content" / "fonts" / "NotoSansJavanese-Regular.ttf"

CONS = {
    "ng": "\ua994", "ny": "\ua99a", "dh": "\ua99d", "th": "\ua99b", "kh": "\ua98f", "sy": "\ua9b1", "h": "\ua9b2",
    "n": "\ua9a4", "c": "\ua995", "r": "\ua9ab", "k": "\ua98f", "d": "\ua9a2", "t": "\ua9a0", "s": "\ua9b1",
    "w": "\ua9ae", "l": "\ua9ad", "p": "\ua9a5", "j": "\ua997", "y": "\ua9aa", "m": "\ua9a9", "g": "\ua992",
    "b": "\ua9a7", "f": "\ua9a5\ua9b3", "v": "\ua9ae\ua9b3", "z": "\ua997\ua9b3", "q": "\ua98f", "x": "\ua98f\ua9c0\ua9b1",
}
VOWEL = {"a": "", "i": "\ua9b6", "u": "\ua9b8", "e": "\ua9bc", "é": "\ua9ba", "è": "\ua9ba", "o": "\ua9ba\ua9b4"}
PANGKON, CECAK, LAYAR, WIGNYAN = "\ua9c0", "\ua981", "\ua982", "\ua983"
CAKRA, PENGKAL = "\ua9bf", "\ua9be"
DIGITS = {str(i): chr(0xA9D0 + i) for i in range(10)}
PUNCT = {",": "\ua9c8", ".": "\ua9c9"}
_TOKEN = re.compile(r"ng|ny|dh|th|kh|sy|[bcdfghjklmnpqrstvwxyz]|[aiueoéè]|\d|[,.]|\s+|.", re.I)


def transliterate(text: str) -> str:
    """Latin title -> Javanese script. Returns "" when nothing is transliterable."""
    norm = unicodedata.normalize("NFC", text.lower())
    toks = _TOKEN.findall(norm)
    out: list[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if t in VOWEL:
            prev = toks[i - 1] if i else ""
            # a vowel on its own is carried by ha; between vowels Javanese writes the glide (bu-wa-ya, si-ya-ng)
            carrier = CONS["w"] if prev in ("u", "o") else CONS["y"] if prev in ("i",) else CONS["h"]
            out.append(carrier + VOWEL[t])
        elif t in CONS:
            if nxt in VOWEL:
                out.append(CONS[t] + VOWEL[nxt])
                i += 1
            elif nxt in ("r", "y") and i + 2 < len(toks) and toks[i + 2] in VOWEL and t not in ("r", "y", "ng", "h"):
                out.append(CONS[t] + (CAKRA if nxt == "r" else PENGKAL) + VOWEL[toks[i + 2]])
                i += 2
            elif t == "ng":
                out.append(CECAK)
            elif t == "r":
                out.append(LAYAR)
            elif t == "h":
                out.append(WIGNYAN)
            else:
                out.append(CONS[t] + PANGKON)
        elif t in DIGITS:
            out.append(DIGITS[t])
        elif t in PUNCT:
            out.append(PUNCT[t])
        elif t.isspace():
            if out and out[-1] != " ":
                out.append(" ")
        i += 1
    return "".join(out).strip()


def has_font() -> bool:
    return FONT.is_file()


@lru_cache(maxsize=8)
def font(size: int) -> Any:
    """Noto Sans Javanese with complex shaping (raqm) so pasangan and sandhangan stack correctly; None if unavailable."""
    from PIL import ImageFont, features

    if not has_font():
        return None
    layout = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    return ImageFont.truetype(str(FONT), size, layout_engine=layout)
