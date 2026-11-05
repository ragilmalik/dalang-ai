"""Capture README screenshots from a running Dalang AI (fake Meta API is fine).

    python scripts/screenshots.py http://localhost:3000      # needs: pip install playwright
The browser is found by scripts/browser_path.py ($CHROME, Playwright's download, or a system Chrome).
Writes docs/screenshots/*.png (phone-sized, 390x844 at 2x). Start the API with FAKE_META_DELAY=1 so the
progress screen is caught mid-run.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_path import launch_kwargs  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
STORY = ("Dulu ada kancil yang pintar. Dia lapar dan mau makan mentimun di seberang sungai. "
         "Tapi di sungai banyak buaya yang lapar juga.")


def wait_status(jid: str, wanted: set[str], timeout: float = 900) -> dict:
    c = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/api/jobs/{jid}").json()
        if j["status"] in wanted:
            return j
        time.sleep(0.5)
    raise TimeoutError(wanted)


with sync_playwright() as p:
    browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)

    page.goto(BASE + "/")
    page.wait_for_selector("text=Jadikan wayang")
    page.screenshot(path=str(OUT / "1-landing.png"))

    page.click("text=Ketik")
    page.fill("textarea", STORY)
    page.click("text=Jadikan wayang")
    page.wait_for_url("**/film/**")
    jid = page.url.rstrip("/").split("/")[-1]
    try:  # catch the progress screen mid-run (scenes being painted)
        page.wait_for_selector("text=/scenes painted and checked/i", timeout=120000)
        time.sleep(0.5)
    except Exception:  # noqa: BLE001 - fast runs may skip past it; take what is on screen
        page.screenshot(path=str(OUT / "debug-progress.png"))
    page.screenshot(path=str(OUT / "2-progress.png"), full_page=True)

    wait_status(jid, {"review"})
    page.reload()
    page.wait_for_selector("text=Storyboard")
    time.sleep(1.5)
    page.screenshot(path=str(OUT / "3-storyboard.png"))

    page.click("text=Bring it to life")
    wait_status(jid, {"done"})
    page.reload()
    page.wait_for_selector("video")
    time.sleep(2)
    page.evaluate("document.querySelector('video').currentTime = 12")
    time.sleep(1.5)
    page.screenshot(path=str(OUT / "4-player.png"))

    # agent trace panel ("Di balik kelir"), opened, on a desktop-width page so the per-call lines fit
    wide = browser.new_page(viewport={"width": 1280, "height": 900})
    wide.goto(f"{BASE}/film/{jid}")
    wide.wait_for_selector("[data-testid=agent-trace]")
    wide.evaluate("document.querySelectorAll('[data-testid=agent-trace], [data-testid=agent-trace] details')"
                  ".forEach(d => d.open = true)")
    time.sleep(0.5)
    trace_panel = wide.query_selector("[data-testid=agent-trace]")
    if trace_panel:
        trace_panel.screenshot(path=str(OUT / "10-agent-trace.png"))
    wide.close()

    # public watch page (Sembah vote + "Behind the puppets" cultural notes) and the gallery
    httpx.post(f"{BASE}/api/jobs/{jid}/share", json={"public": True}, trust_env=False, timeout=30).raise_for_status()
    page.goto(f"{BASE}/watch/{jid}")
    page.wait_for_selector("text=Sembah")
    page.click("text=Sembah")
    time.sleep(1)
    page.screenshot(path=str(OUT / "5-watch.png"), full_page=True)
    page.goto(f"{BASE}/gallery")
    time.sleep(2)
    page.screenshot(path=str(OUT / "6-gallery.png"))

    # Gara-gara: a second film with the choice turned on, caught at the pause
    api = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
    g = api.post("/api/jobs", data={"text": STORY + " Kancil bilang raja mau menghitung semua buaya.", "language": "id",
                                    "review": "true", "gara_gara": "true"}).json()
    wait_status(g["id"], {"choice"})
    page.goto(f"{BASE}/film/{g['id']}")
    page.wait_for_selector("text=Gara-gara!")
    time.sleep(2)
    page.evaluate("window.scrollTo(0, 260)")
    time.sleep(0.8)
    page.screenshot(path=str(OUT / "7-garagara.png"))

    # Kotak Wayang: keep Kancil from the first film in this browser's family box
    family = page.evaluate("() => { let f = localStorage.getItem('dalang_family');"
                           " if (!f) { f = 'fam_' + crypto.randomUUID().replaceAll('-', ''); localStorage.setItem('dalang_family', f); }"
                           " return f; }")
    api.post("/api/kotak", json={"family_id": family, "job_id": jid, "char_id": "kancil"}).raise_for_status()
    page.goto(f"{BASE}/kotak")
    page.wait_for_selector("text=Bawa kembali")
    page.click("text=Bawa kembali")
    time.sleep(1)
    page.screenshot(path=str(OUT / "8-kotak.png"))
    browser.close()

    # Printable puppets: page 2 of the PDF (first puppet with its dashed cut line)
    import shutil
    import subprocess

    pdf = OUT.parent / "_puppets.pdf"
    pdf.write_bytes(api.get(f"/api/jobs/{jid}/puppets.pdf").content)
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", "70", "-f", "2", "-l", "2", "-singlefile", str(pdf),
                        str(OUT / "9-puppets-pdf")], check=True)
    pdf.unlink(missing_ok=True)
print("saved", sorted(x.name for x in OUT.iterdir()))
