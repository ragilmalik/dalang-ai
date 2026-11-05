"""Penjaga Budaya (guardian of culture): a cultural-review agent between the lakon and the drawing.

Muse Spark reads the whole script against a small curated rules file (content/cultural_rules.json: gentle conflict,
no politics, no gore, respect for wayang figures, child-friendly pictures, character canon, no invented ritual,
respect for the gunungan) and returns, per scene and per character, pass/fail, the rule ids it broke and fixed
text. The fixes are written back into the script BEFORE Muse Image draws anything, so a wrong depiction never
costs a picture. A deterministic word scan of the same rules runs before (as a hint for the model) and after
(as a guarantee: anything still matching is scrubbed with the rules file's gentle replacements).
Every finding and fix is an agent decision in the film's trace."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from .. import cost, meta_client
from ..config import settings
from ..jobs import Job
from ..schemas import Script

log = logging.getLogger("dalang.penjaga")
RULES_FILE = Path(__file__).resolve().parents[2] / "content" / "cultural_rules.json"
SCENE_FIELDS = ("narration", "action", "image_prompt")
CHAR_FIELDS = ("visual_description", "cultural_note")


@lru_cache(maxsize=1)
def rules() -> dict[str, Any]:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def rule_ids() -> list[str]:
    return [r["id"] for r in rules()["rules"]]


def _word_re(word: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])", re.I)


def _hits(text: str, field: str) -> list[tuple[str, str]]:
    """(rule id, word) for every rules-file word found in this field's text."""
    out = []
    for r in rules()["rules"]:
        if field not in r["fields"]:
            continue
        for word in r["replace"]:
            if _word_re(word).search(text or ""):
                out.append((r["id"], word))
    return out


def _canon_hits(text: str) -> list[tuple[str, str]]:
    low = (text or "").lower()
    out = []
    for c in rules()["canon"]:
        if any(m in low for m in c["match"]):
            out += [("canon", f"{c['name']}: {w}") for w in c["avoid"] if _word_re(w).search(low)]
    return out


def scan(script: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic pre-screen: every rules-file word or canon violation, with where it was found."""
    found = []
    for sc in script.get("scenes", []):
        for f in SCENE_FIELDS:
            for rid, word in _hits(sc.get(f, ""), f):
                found.append({"scene": sc["n"], "field": f, "rule": rid, "word": word})
        text = " ".join(sc.get(f, "") for f in SCENE_FIELDS)
        found += [{"scene": sc["n"], "field": "scene", "rule": rid, "word": w} for rid, w in _canon_hits(text)]
    for ch in script.get("characters", []):
        for f in CHAR_FIELDS:
            for rid, word in _hits(ch.get(f, ""), f):
                found.append({"character": ch["id"], "field": f, "rule": rid, "word": word})
        text = " ".join([ch.get("name", "")] + [ch.get(f, "") for f in CHAR_FIELDS])
        found += [{"character": ch["id"], "field": "character", "rule": rid, "word": w} for rid, w in _canon_hits(text)]
    return found


def _keep_case(gentle: str) -> Callable[[re.Match[str]], str]:
    def sub(m: re.Match[str]) -> str:
        return gentle[:1].upper() + gentle[1:] if m.group(0)[:1].isupper() else gentle
    return sub


def scrub(text: str, field: str) -> str:
    """Replace every rules-file word in this field with its gentle replacement (keeping a capital first letter)."""
    for r in rules()["rules"]:
        if field not in r["fields"]:
            continue
        for word, gentle in r["replace"].items():
            text = _word_re(word).sub(_keep_case(gentle), text)
    return text


SYSTEM = """You are Penjaga Budaya, the guardian of culture for a children's wayang kulit film (ages 5-12).
You review a finished script BEFORE any picture is drawn. Check every scene (narration, action, image_prompt) and
every character (visual_description, cultural_note) against the rules below. Keep the child's idea and plot;
change only what breaks a rule, as little as possible, in the same language as the original text.
For each scene and character return passed, the ids of the rules it breaks, a short issue, and the fixed
fields ("" for a field that needs no change). Narration stays 1-2 sentences, max 32 words."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scenes": {"type": "array", "items": {"type": "object", "properties": {
            "n": {"type": "integer"}, "passed": {"type": "boolean"},
            "rules": {"type": "array", "items": {"type": "string"}}, "issue": {"type": "string"},
            "narration": {"type": "string"}, "action": {"type": "string"}, "image_prompt": {"type": "string"}},
            "required": ["n", "passed", "rules", "issue", "narration", "action", "image_prompt"]}},
        "characters": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "passed": {"type": "boolean"},
            "rules": {"type": "array", "items": {"type": "string"}}, "issue": {"type": "string"},
            "visual_description": {"type": "string"}, "cultural_note": {"type": "string"}},
            "required": ["id", "passed", "rules", "issue", "visual_description", "cultural_note"]}},
        "note": {"type": "string"},
    },
    "required": ["scenes", "characters", "note"],
}


def rules_text() -> str:
    lines = [f"- {r['id']}: {r['guidance']}" for r in rules()["rules"]]
    lines.append("Canon (keep each known character recognisable):")
    lines += [f"  * {c['name']}: {c['keep']}" for c in rules()["canon"]]
    return "\n".join(lines)


def user_message(script: dict[str, Any], hints: list[dict[str, Any]], only: set[int] | None) -> str:
    part = {"title": script.get("title"), "language": script.get("language"),
            "characters": [{k: c.get(k, "") for k in ("id", "name", "wayang_archetype", *CHAR_FIELDS)}
                           for c in script.get("characters", [])],
            "scenes": [{k: s.get(k, "") for k in ("n", "setting", *SCENE_FIELDS)} for s in script.get("scenes", [])
                       if only is None or s["n"] in only]}
    hint = "\n".join(f"- {h.get('scene') or h.get('character')} {h['field']}: rule {h['rule']} ({h['word']})"
                     for h in hints) or "- none"
    return (f"Rules:\n{rules_text()}\n\nWord scan hints (may be incomplete):\n{hint}\n\n"
            f"SCRIPT JSON:\n{json.dumps(part, ensure_ascii=False)}")


def _clip_words(text: str, n: int = 32) -> str:
    words = text.split()
    return " ".join(words[:n])


def run(job: Job, script: Script, only: set[int] | None = None) -> Script:
    """Review the script against the cultural rules, write the fixes back, and record a report on the job.
    only: review just these scene numbers (after a gara-gara rewrite). CULTURAL_REVIEW=0 turns it off."""
    if not settings.cultural_review:
        return script
    meter = cost.current()
    if meter is None:
        return _run(job, script, only)
    old = meter.stage_of
    meter.stage_of = lambda: "lakon"  # the review belongs to the lakon stage in the trace
    try:
        return _run(job, script, only)
    finally:
        meter.stage_of = old


def _run(job: Job, script: Script, only: set[int] | None) -> Script:
    data = script.model_dump()
    n_rules = len(rules()["rules"])
    before = next((st["detail"] for st in job.s["stages"] if st["key"] == "lakon"), "") or ""
    in_scope = [s for s in data["scenes"] if only is None or s["n"] in only]
    hints = [h for h in scan(data) if "character" in h or only is None or h["scene"] in only]
    model_ok = True
    review: dict[str, Any] = {"scenes": [], "characters": [], "note": ""}
    try:
        with cost.labelled("Penjaga Budaya"):
            raw = meta_client.chat_json(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_message(data, hints, only)}],
                SCHEMA, "cultural_review", model=settings.culture_model, reasoning_effort="low")
        if isinstance(raw, dict):
            review = raw
        job.used(settings.culture_model)
    except cost.BudgetExceeded:
        raise
    except Exception as e:  # noqa: BLE001 - the word scan still guards the script
        model_ok = False
        log.warning("cultural review call failed: %s", e)
        cost.record_decision(f"model review unavailable ({str(e)[:80]}); the rules-file word scan guards the script",
                             agent="penjaga")

    flagged: dict[int, set[str]] = {}
    for h in hints:
        if "scene" in h:
            flagged.setdefault(h["scene"], set()).add(h["rule"])
    fixes = 0
    scene_rows = []
    by_n = {s["n"]: s for s in data["scenes"]}
    for r in review.get("scenes") or []:
        sc = by_n.get(int(r.get("n", 0) or 0))
        if sc is None or (only is not None and sc["n"] not in only):
            continue
        if not r.get("passed", True):
            flagged.setdefault(sc["n"], set()).update(str(x) for x in r.get("rules") or ["model"])
            changed = []
            for f in SCENE_FIELDS:
                new = str(r.get(f) or "").strip()
                if new and new != sc[f]:
                    sc[f] = _clip_words(new) if f == "narration" else new[:400]
                    changed.append(f)
            if changed:
                fixes += 1
                cost.record_decision(f"scene {sc['n']} broke {', '.join(r.get('rules') or ['a rule'])}"
                                     f" ({str(r.get('issue', ''))[:100]}); fixed {', '.join(changed)} before drawing",
                                     agent="penjaga")
    chars = {c["id"]: c for c in data["characters"]}
    char_flags: dict[str, set[str]] = {}
    for h in hints:
        if "character" in h:
            char_flags.setdefault(h["character"], set()).add(h["rule"])
    for r in review.get("characters") or []:
        ch = chars.get(str(r.get("id", "")))
        if ch is None or r.get("passed", True):
            continue
        char_flags.setdefault(ch["id"], set()).update(str(x) for x in r.get("rules") or ["model"])
        changed = []
        for f in CHAR_FIELDS:
            new = str(r.get(f) or "").strip()
            if new and new != ch[f]:
                ch[f] = new[:300]
                changed.append(f)
        if changed:
            fixes += 1
            cost.record_decision(f"{ch['name']} broke {', '.join(r.get('rules') or ['a rule'])}"
                                 f" ({str(r.get('issue', ''))[:100]}); fixed {', '.join(changed)} before drawing",
                                 agent="penjaga")

    # guarantee: whatever still matches a rules-file word is scrubbed
    leftover = [h for h in scan(data) if "character" in h or only is None or h["scene"] in only]
    for h in leftover:
        if "scene" in h and h["field"] in SCENE_FIELDS:
            by_n[h["scene"]][h["field"]] = scrub(by_n[h["scene"]][h["field"]], h["field"])
        elif "character" in h and h["field"] in CHAR_FIELDS:
            chars[h["character"]][h["field"]] = scrub(chars[h["character"]][h["field"]], h["field"])
    if leftover:
        fixes += 1
        words = ", ".join(sorted({h["word"] for h in leftover}))[:120]
        cost.record_decision(f"word scan still found {words}; replaced with the rules file's gentle words",
                             agent="penjaga")
    remaining = scan(data)
    for sc in in_scope:
        n = sc["n"]
        rule_hits = sorted(flagged.get(n, set()))
        scene_rows.append({"n": n, "passed_first": not rule_hits, "rules": rule_hits,
                           "passed_after": not any(h.get("scene") == n and h["field"] in SCENE_FIELDS for h in remaining)})
    char_rows = [{"id": c["id"], "name": c["name"], "passed_first": not char_flags.get(c["id"]),
                  "rules": sorted(char_flags.get(c["id"], set()))} for c in data["characters"]]
    total = len(scene_rows) or 1
    report = {
        "model": settings.culture_model if model_ok else None, "rules": rule_ids(), "rules_status": rules()["status"],
        "scenes": scene_rows, "characters": char_rows, "fixes": fixes,
        "pass_rate_first": round(sum(r["passed_first"] for r in scene_rows) / total, 3),
        "pass_rate_after": round(sum(r["passed_after"] for r in scene_rows) / total, 3),
        "note": str(review.get("note") or "")[:300],
    }
    if only is not None and job.s.get("cultural_review"):  # gara-gara: keep the first review's rows for kept scenes
        old = [r for r in job.s["cultural_review"].get("scenes", []) if r["n"] not in only]
        report["scenes"] = sorted(old + scene_rows, key=lambda r: r["n"])
        report["fixes"] += int(job.s["cultural_review"].get("fixes", 0))
        allrows = report["scenes"] or [{}]
        report["pass_rate_first"] = round(sum(bool(r.get("passed_first")) for r in allrows) / len(allrows), 3)
        report["pass_rate_after"] = round(sum(bool(r.get("passed_after")) for r in allrows) / len(allrows), 3)
    if not fixes:
        cost.record_decision(f"all {len(scene_rows)} scenes and {len(char_rows)} puppets pass the {n_rules} cultural rules",
                             agent="penjaga")
    fixed = Script(**data)
    job.set(script=fixed.model_dump(), cultural_review=report)
    passed = sum(r["passed_first"] for r in scene_rows)
    job.stage("lakon", detail=(before.split(" \u00b7 Penjaga Budaya")[0] +
                               f" \u00b7 Penjaga Budaya: {passed}/{len(scene_rows)} scenes passed first time, {fixes} fixed"))
    return fixed
