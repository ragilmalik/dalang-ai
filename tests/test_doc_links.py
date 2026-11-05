"""Every relative link in the tracked Markdown docs must point at a file that exists."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _markdown() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if (ROOT / line).is_file()]


def _broken(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    bad = []
    for target in LINK.findall(text):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target):
            continue
        rel = target.split("#", 1)[0].split("?", 1)[0]
        if rel and not (path.parent / rel).exists():
            bad.append(f"{path.relative_to(ROOT)} -> {target}")
    return bad


def test_relative_markdown_links_resolve():
    broken = [b for p in _markdown() for b in _broken(p)]
    assert broken == []
