"""Phone (390) and desktop (1440) screenshots of every main page, for UI reviews.

    python web/e2e/ui_shots.py http://127.0.0.1:3207 docs/screenshots/ui/after

Makes its own films on the fake-Meta API behind the site (one finished and shared, one waiting at a gara-gara
question, one waiting at the storyboard, one still being made), unless UI_FILM / UI_GARA / UI_REVIEW are set.
Writes <out>/<page>-phone.png and <out>/<page>-desktop.png (full page) and prints the list.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_path import launch_kwargs  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3207"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/screenshots/ui/after")
ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
api = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
TALE = "Kancil yang cerdik ingin menyeberang sungai penuh buaya untuk makan mentimun di seberang."


def make(text: str, **extra: str) -> str:
    r = api.post("/api/jobs", data={"text": text, "language": "id", "review": "false", **extra})
    r.raise_for_status()
    return r.json()["id"]


def wait(jid: str, want: set[str], limit: float = 600) -> dict:
    t0 = time.time()
    while True:
        j = api.get(f"/api/jobs/{jid}").json()
        if j["status"] in want | {"failed", "blocked"} or time.time() - t0 > limit:
            return j
        time.sleep(1)


def main() -> int:
    from playwright.sync_api import sync_playwright

    film = os.environ.get("UI_FILM") or make(TALE)
    gara = os.environ.get("UI_GARA") or make("Kancil bertemu buaya lagi di sungai, lalu mereka bermain bersama.",
                                              gara_gara="true")
    review = os.environ.get("UI_REVIEW") or make(TALE, review="true")
    wait(film, {"done"})
    api.post(f"/api/jobs/{film}/share", json={"public": True})
    wait(gara, {"choice"})
    wait(review, {"review"})
    # still being made when we look at it (only made when that page is wanted: every film costs money on live)
    working = make(TALE) if not ONLY or "film-working" in ONLY else "none"
    pages = [
        ("home", "/", "[data-testid=hero-tell]"),
        ("film-working", f"/film/{working}", "[data-testid=pipeline-theatre]"),
        ("film-storyboard", f"/film/{review}", "textarea"),
        ("film-gara", f"/film/{gara}", "#gara-title"),
        ("film-done", f"/film/{film}", "video"),
        ("watch", f"/watch/{film}", "video"),
        ("kelir", f"/kelir/{film}", "[data-testid=kelir][data-ready='1']"),
        ("vote", f"/vote/{gara}", "h1"),
        ("gallery", "/gallery", "main"),
        ("pentas", "/pentas", "[data-testid=pentas-wall]"),
        ("kotak", "/kotak", "main h1"),
        ("guru", "/guru", "main h1"),
        ("judge", "/judge", "main h1"),
        ("404", "/tidak-ada", "main"),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
        for vp, size, scale in (("phone", (390, 844), 2), ("desktop", (1440, 900), 1)):
            ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=scale,
                                      service_workers="block", reduced_motion="reduce")
            page = ctx.new_page()
            for name, path, ready in pages:
                if ONLY and name not in ONLY:
                    continue
                page.goto(BASE + path, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector(ready, timeout=30000)
                except Exception as e:  # noqa: BLE001
                    print(f"  {name}: {ready} not found ({type(e).__name__})")
                page.wait_for_timeout(1500)
                f = OUT / f"{name}-{vp}.png"
                page.screenshot(path=str(f), full_page=True)
                shots.append(str(f))
                print(f, flush=True)
            ctx.close()
        browser.close()
    print(f"{len(shots)} screenshots; films: done {film}, gara {gara}, review {review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
