"""House style: no em dashes in anything tracked in the repo (docs, code, web copy, scripts)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = "\u2014"
TEXT_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".js", ".json", ".css", ".yml", ".yaml", ".sh", ".txt", ".toml", ".html"}


def _tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if (ROOT / line).suffix in TEXT_SUFFIXES]


def test_no_em_dashes_in_tracked_text():
    offenders = []
    for path in _tracked():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if EM_DASH in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
