"""Find a Chromium the recorders can drive, without hardcoding a path.

Order: $CHROME, Playwright's own download (``python -m playwright install chromium``), then a system
Chrome/Chromium on PATH or in the usual install folders. Returns None when nothing usable exists, so callers
can fall back (make_demo_video.py then renders from the finished film and stills with ffmpeg only).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "msedge")
_FOLDERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
)


def playwright_bundled() -> str | None:
    """Path of Playwright's downloaded Chromium if it is really on disk."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            exe = p.chromium.executable_path
    except Exception:  # noqa: BLE001 - a broken install just means "not available"
        return None
    return exe if exe and Path(exe).exists() else None


def find_chromium() -> str | None:
    """Return an executable path, or "" meaning "let Playwright use its bundled browser", or None."""
    env = os.environ.get("CHROME", "").strip()
    if env and Path(env).exists():
        return env
    if playwright_bundled():
        return ""
    for name in _NAMES:
        hit = shutil.which(name)
        if hit:
            return hit
    for p in _FOLDERS:
        if Path(p).exists():
            return p
    return None


def launch_kwargs() -> dict[str, object]:
    """Keyword arguments for ``p.chromium.launch``; raises RuntimeError when no browser is available."""
    exe = find_chromium()
    if exe is None:
        raise RuntimeError("No Chromium found. Run `python -m playwright install chromium`, install Chrome, "
                           "or set CHROME=/path/to/chrome.")
    kw: dict[str, object] = {"args": ["--no-sandbox"]}
    if exe:
        kw["executable_path"] = exe
    return kw


if __name__ == "__main__":
    print(find_chromium())
