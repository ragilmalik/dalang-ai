"""scripts/voice_check.py: the word scan finds what it should, skips what it should, and the repo is clean."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("voice_check", ROOT / "scripts" / "voice_check.py")
assert spec and spec.loader
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


def _scan(tmp_path: Path, name: str, text: str) -> list[tuple[int, str, str]]:
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return vc.scan(f)


def test_markdown_words_agent_talk_and_dashes(tmp_path: Path) -> None:
    hits = _scan(tmp_path, "a.md", "We delve into it.\nThe agent should rerun this.\nTwo \u2014 three.\nFine line.\n")
    assert {(n, k) for n, k, _ in hits} == {(1, "ai-word"), (2, "agent"), (3, "dash")}


def test_app_features_named_agent_are_not_flagged(tmp_path: Path) -> None:
    text = "Open the agent trace.\nEach fix is an agent decision.\nWonder is the agentic model.\n"
    assert _scan(tmp_path, "b.md", text) == []


def test_code_blocks_and_inline_code_are_skipped(tmp_path: Path) -> None:
    assert _scan(tmp_path, "c.md", "```\nleverage\n```\nRun `robust` here.\n") == []


def test_python_reads_comments_and_docstrings_only(tmp_path: Path) -> None:
    code = '"""Seamless module."""\nPROMPT = "You MUST answer, leverage it"\nx = 1  # crucial step\n'
    hits = _scan(tmp_path, "d.py", code)
    assert sorted(w.lower() for _n, _k, w in hits) == ["crucial", "seamless"]


def test_ts_comments_and_dashes_in_ui_text(tmp_path: Path) -> None:
    code = 'const url = "https://x.y/z"; // a robust check\nconst t = "2\u20134 min";\n'
    kinds = sorted(k for _n, k, _w in _scan(tmp_path, "e.tsx", code))
    assert kinds == ["ai-word", "dash"]


def test_voice_ok_marker_keeps_a_line(tmp_path: Path) -> None:
    assert _scan(tmp_path, "f.md", "A quoted error says delve. <!-- voice-ok -->\n") == []


def test_repo_has_no_hits() -> None:
    hits = [(str(p), h) for p in vc.files_to_scan([]) for h in vc.scan(p)]
    assert hits == []
