"""One source for the numbers the docs quote (test count, e2e steps, coverage, demo length, axe page checks).

    python scripts/facts.py                       # measure what is cheap (tests, demo length) and rewrite the docs
    python scripts/facts.py --e2e-log e2e.log     # also take the e2e result ("N/N passed") from a smoke-test log
    python scripts/facts.py --coverage 81         # record a coverage percentage (from `make coverage`)
    python scripts/facts.py --check               # exit 1 if any doc disagrees with docs/facts.json (used by tests)

Docs mark a number like this: <!-- facts:tests -->127<!-- /facts -->. Only the text between the two markers is
rewritten, so the sentence around it stays hand-written. Values that cannot be measured now keep their last value.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "docs" / "facts.json"
DEMO = ROOT / "docs" / "demo" / "dalang-ai-demo.mp4"
MARK = re.compile(r"<!-- facts:([a-z0-9_]+) -->(.*?)<!-- /facts -->", re.S)


def doc_files() -> list[Path]:
    """Every markdown file that may carry fact markers."""
    files = [ROOT / "README.md", ROOT / "README.id.md", *sorted((ROOT / "docs").glob("*.md"))]
    return [p for p in files if p.exists()]


def count_tests() -> int | None:
    """Number of pytest tests, from `pytest --collect-only -q` (no test runs)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    m = re.search(r"(\d+) tests? collected", r.stdout)
    return int(m.group(1)) if m else None


def demo_seconds() -> float | None:
    """Length of the committed demo video, from ffprobe."""
    if not DEMO.exists():
        return None
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(DEMO)],
                           capture_output=True, text=True, timeout=60)
        return round(float(r.stdout.strip()), 1)
    except (OSError, ValueError):
        return None


def a11y_checks() -> int | None:
    """Number of axe page checks (one table row per page and screen) in docs/ACCESSIBILITY.md."""
    doc = ROOT / "docs" / "ACCESSIBILITY.md"
    if not doc.exists():
        return None
    rows = re.findall(r"^\| [^|]+ \| (?:phone|desktop) \|", doc.read_text(), re.M)
    return len(rows) or None


def e2e_from_log(path: Path) -> str | None:
    """'22/22' from the last 'N/M passed' line of a smoke-test log."""
    found = re.findall(r"^(\d+)/(\d+) passed", path.read_text(errors="replace"), re.M)
    return f"{found[-1][0]}/{found[-1][1]}" if found else None


def load() -> dict[str, Any]:
    return json.loads(FACTS.read_text()) if FACTS.exists() else {}


def rendered(facts: dict[str, Any]) -> dict[str, str]:
    """The text each marker shows."""
    out = {k: str(v) for k, v in facts.items() if not isinstance(v, (dict, list))}
    if isinstance(facts.get("demo_seconds"), (int, float)):
        s = round(float(facts["demo_seconds"]))
        out["demo_length"] = f"{s // 60}:{s % 60:02d}"
    out["coverage"] = f"{facts['coverage']}%" if "coverage" in facts else "n/a"
    return out


def rewrite(text: str, values: dict[str, str]) -> str:
    return MARK.sub(lambda m: f"<!-- facts:{m.group(1)} -->{values.get(m.group(1), m.group(2))}<!-- /facts -->", text)


def stale(values: dict[str, str]) -> list[str]:
    """Markers whose text differs from facts.json, as 'file: key shows X, facts say Y'."""
    bad = []
    for f in doc_files():
        for m in MARK.finditer(f.read_text()):
            want = values.get(m.group(1))
            if want is None:
                bad.append(f"{f.name}: unknown fact '{m.group(1)}'")
            elif m.group(2) != want:
                bad.append(f"{f.name}: {m.group(1)} shows {m.group(2)!r}, facts say {want!r}")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--e2e-log")
    ap.add_argument("--coverage", type=float)
    ap.add_argument("--no-measure", action="store_true", help="only rewrite docs from facts.json")
    a = ap.parse_args(argv)
    facts = load()
    if a.check:
        bad = stale(rendered(facts))
        print("\n".join(bad) or "docs agree with docs/facts.json")
        return 1 if bad else 0
    if not a.no_measure:
        for key, fn in (("tests", count_tests), ("demo_seconds", demo_seconds), ("a11y", a11y_checks)):
            v = fn()
            if v is not None:
                facts[key] = v
    if a.e2e_log and (e2e := e2e_from_log(Path(a.e2e_log))):
        facts["e2e"] = e2e
    if a.coverage is not None:
        facts["coverage"] = round(a.coverage)
    FACTS.write_text(json.dumps(dict(sorted(facts.items())), indent=1) + "\n")
    values = rendered(facts)
    changed = []
    for f in doc_files():
        old = f.read_text()
        new = rewrite(old, values)
        if new != old:
            f.write_text(new)
            changed.append(f.name)
    print(json.dumps(facts), "| rewrote:", ", ".join(changed) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
