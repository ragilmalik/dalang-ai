"""Rough linter for AI-sounding prose in docs. Counts, doesn't judge. Not wired into CI.

    python scripts/slop_check.py README.md docs/*.md          # per-file table
    python scripts/slop_check.py --json README.md > out.json  # same, as JSON
    python scripts/slop_check.py --hits README.md             # print each banned word / contrast it found

Columns: words, em/en dashes per 1k words, banned words, not-X-but-Y contrasts, share of bullets that open with a
bold label ("- **Thing:** ..."), clipped contrasts (", not X", "rather than", "instead of"), agent-workflow
traces (subagent, orchestrator, round-N), title-case headings, emoji headings. Code blocks and inline code are skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BANNED = [
    "seamless", "seamlessly", "robust", "leverage", "leverages", "leveraging", "delve", "delves", "empower",
    "empowers", "empowering", "unlock", "unlocks", "elevate", "elevates", "tapestry", "vibrant", "testament",
    "showcase", "showcases", "showcasing", "journey", "crucial", "pivotal", "cutting-edge", "game-changer",
    "game changer", "groundbreaking", "meticulous", "meticulously", "additionally", "furthermore", "moreover",
    "in conclusion", "overall", "ultimately", "here's the thing", "whether you're", "breathtaking", "stunning",
    "nestled", "rich cultural", "underscore", "underscores", "harness", "harnesses", "landscape", "realm",
    "transformative", "revolutionize", "revolutionary", "magic", "magical", "i hope this helps", "let's dive",
]
BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b", re.I)
CONTRAST_RE = re.compile(
    r"\bnot (?:just|only|merely|simply)\b[^.\n]{0,80}\bbut\b"
    r"|\b(?:it's|it is|this is|that's|that is)n?'?t? not\b[^.\n]{0,60}[,;:] (?:it's|it is)\b"
    r"|\bisn't (?:just )?(?:a|an|the)\b[^.\n]{0,60}[.;,] (?:it's|it is)\b"
    r"|\bnot (?:a|an)\b[^.\n]{0,40}, but (?:a|an)\b"
    r"|\bbukan (?:hanya|sekadar|cuma)\b[^.\n]{0,80}\b(?:tapi|tetapi|melainkan)\b",
    re.I,
)
CLIPPED_RE = re.compile(r"[,;(] not (?:a|an|the|just|only)?\s?\w+|\brather than\b|\binstead of\b", re.I)
AGENT_RE = re.compile(r"\bsub-?agents?\b|\borchestrat\w*|\br5-(?:core|web|fin\w*)|\bthe AI assistant\b|\bas requested\b|\bround[- ]\d\b", re.I)
DASH_RE = re.compile(r"[\u2014\u2013]| -- ")
BOLD_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\*\*[^*]{1,60}\*\*\s*[:.\u2013\u2014-]", re.M)
BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S", re.M)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.M)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
SMALL = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "vs", "via", "per", "is"}


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    return re.sub(r"https?://\S+", " ", text)


def title_case(heading: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", heading)]
    if len(words) < 3:
        return False
    rest = [w for w in words[1:] if w.lower() not in SMALL]
    caps = [w for w in rest if w[0].isupper() and not w.isupper()]
    return len(rest) >= 2 and len(caps) / len(rest) >= 0.75


def check(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_code(raw)
    words = len(re.findall(r"\w+", text))
    bullets = len(BULLET_RE.findall(text))
    heads = HEADING_RE.findall(text)
    return {
        "file": str(path),
        "words": words,
        "dashes_per_1k": round(1000 * len(DASH_RE.findall(text)) / max(words, 1), 1),
        "banned": len(BANNED_RE.findall(text)),
        "contrast": len(CONTRAST_RE.findall(text)),
        "clipped": len(CLIPPED_RE.findall(text)),
        "agent_trace": len(AGENT_RE.findall(raw)),
        "bold_bullets_pct": round(100 * len(BOLD_BULLET_RE.findall(text)) / bullets) if bullets else 0,
        "title_case_h": sum(title_case(h) for h in heads),
        "emoji_h": sum(bool(EMOJI_RE.search(h)) for h in heads),
        "_hits": [m.group(0) for m in BANNED_RE.finditer(text)] + [m.group(0) for m in CONTRAST_RE.finditer(text)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--hits", action="store_true")
    a = ap.parse_args()
    rows = [check(p) for p in a.files if p.is_file()]
    if a.json:
        json.dump([{k: v for k, v in r.items() if k != "_hits"} for r in rows], sys.stdout, indent=1)
        return 0
    cols = ["words", "dashes_per_1k", "banned", "contrast", "clipped", "agent_trace", "bold_bullets_pct", "title_case_h", "emoji_h"]
    print("file".ljust(48) + "".join(c[:10].rjust(11) for c in cols))
    for r in rows:
        print(r["file"][-48:].ljust(48) + "".join(str(r[c]).rjust(11) for c in cols))
        if a.hits and r["_hits"]:
            print("    " + " | ".join(r["_hits"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
