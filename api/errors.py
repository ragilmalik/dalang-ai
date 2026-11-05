"""What a family sees when something breaks: a short, kind, bilingual message per kind of failure, never the raw
exception text, an exception class name or a server path. The full traceback goes to the server log only."""
from __future__ import annotations

import re

# kind id -> "Bahasa Indonesia · English"
MESSAGES: dict[str, str] = {
    "meta": ("Ki Dalang tidak bisa menghubungi model Meta sekarang. Coba lagi sebentar lagi, ya! \u00b7 "
             "Ki Dalang could not reach the Meta models just now. Please try again in a moment."),
    "budget": ("Batas biaya untuk film ini sudah tercapai, jadi Ki Dalang berhenti. \u00b7 "
               "This film reached its budget limit, so Ki Dalang stopped."),
    "script": ("Ki Dalang belum bisa menulis lakon dari cerita ini. Coba ceritakan lagi, ya! \u00b7 "
               "Ki Dalang could not write a play from this story. Please try telling it again."),
    "picture": ("Ada gambar yang rusak saat disimpan. Coba lagi, ya! \u00b7 "
                "A picture got damaged while it was being saved. Please try again."),
    "internal": ("Ki Dalang tersandung saat membuat filmmu. Coba lagi, ya! \u00b7 "
                 "Ki Dalang stumbled while making your film. Please try again."),
}


def kind_of(e: BaseException) -> str:
    """Sort an exception into one of MESSAGES' kinds (by type first, then by well-known wording)."""
    from . import cost, meta_client

    text = str(e)
    if isinstance(e, cost.BudgetExceeded):
        return "budget"
    if isinstance(e, meta_client.MetaAPIError) or type(e).__module__.startswith("httpx") \
            or "from https://" in text or "circuit open" in text or text.startswith("Request to http"):
        return "meta"
    try:
        from PIL import UnidentifiedImageError
        if isinstance(e, UnidentifiedImageError):
            return "picture"
    except ImportError:  # pragma: no cover - Pillow is a hard dependency
        pass
    if "invalid" in text.lower() and ("script" in text.lower() or "lakon" in text.lower() or "twice" in text.lower()):
        return "script"
    if "budget" in text.lower():
        return "budget"
    return "internal"


def public(e: BaseException) -> tuple[str, str]:
    """(kind, bilingual message) safe to put in job state, the stage trace and the API."""
    kind = kind_of(e)
    return kind, MESSAGES[kind]


# An absolute filesystem path: starts at a "/" that is not part of a URL or a word ("id/en", "1/5" and
# "https://host/v1/x" are left alone) and has at least two segments. /media/... and /api/... are public URLs.
_PATH = re.compile(r"(?<![\w:/.\-])(?!/media/|/api/)(?:/[\w.\-@+]+){2,}/?")
_WINPATH = re.compile(r"\b[A-Za-z]:\\[^\s'\"]+")
# Exception class names such as UnidentifiedImageError, PIL.UnidentifiedImageError, json.JSONDecodeError
_EXC = re.compile(r"\b(?:[A-Za-z_]\w*\.)*[A-Z]\w*(?:Error|Exception)\b:?\s*")


def scrub(text: str) -> str:
    """Remove server paths, exception class names and traceback text from a detail a family can see."""
    if not text:
        return text
    if "Traceback (most recent call last)" in text:
        text = text.split("Traceback (most recent call last)")[0].strip() or "internal error"
    text = _PATH.sub("[file]", text)
    text = _WINPATH.sub("[file]", text)
    text = _EXC.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()
