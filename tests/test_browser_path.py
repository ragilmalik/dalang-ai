"""The recorders find a browser without a hardcoded path, and say clearly when there is none."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import browser_path  # noqa: E402


def test_env_chrome_wins(monkeypatch, tmp_path):
    exe = tmp_path / "chrome"
    exe.write_text("")
    monkeypatch.setenv("CHROME", str(exe))
    assert browser_path.find_chromium() == str(exe)
    assert browser_path.launch_kwargs()["executable_path"] == str(exe)


def test_missing_env_path_is_ignored(monkeypatch):
    monkeypatch.setenv("CHROME", "/no/such/chrome")
    monkeypatch.setattr(browser_path, "playwright_bundled", lambda: None)
    monkeypatch.setattr(browser_path.shutil, "which", lambda n: None)
    monkeypatch.setattr(browser_path, "_FOLDERS", ())
    assert browser_path.find_chromium() is None
    with pytest.raises(RuntimeError, match="playwright install chromium"):
        browser_path.launch_kwargs()


def test_bundled_playwright_uses_no_executable_path(monkeypatch):
    monkeypatch.delenv("CHROME", raising=False)
    monkeypatch.setattr(browser_path, "playwright_bundled", lambda: "/pw/chrome")
    assert browser_path.launch_kwargs() == {"args": ["--no-sandbox"]}


def test_system_browser_on_path(monkeypatch):
    monkeypatch.delenv("CHROME", raising=False)
    monkeypatch.setattr(browser_path, "playwright_bundled", lambda: None)
    monkeypatch.setattr(browser_path.shutil, "which", lambda n: "/usr/bin/chromium" if n == "chromium" else None)
    assert browser_path.find_chromium() == "/usr/bin/chromium"
