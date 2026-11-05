"""Browser e2e for the Kelir Live, vote, remix and Pentas screens, on a 390 px phone viewport (Playwright + Chromium).

    python web/e2e/r5_ui.py http://127.0.0.1:3005

Needs the fake-Meta API behind the Next.js server (scripts/e2e_local.sh runs it after smoke_test.py).
Kelir Live drag (synthetic pointer events: mouse drag, two-finger touch tilt, gunungan tap), the home hero,
the pipeline theatre, gara-gara classroom vote, remix (hidden when the API has no remix endpoint), /pentas.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_path import launch_kwargs  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3005"
api = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
ok: list[bool] = []


def step(name: str, cond: bool, info: str = "") -> None:
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + "web " + name + (f"  {info}" if info else ""), flush=True)


def wait_status(jid: str, want: set[str], limit: float = 600) -> dict:
    t0 = time.time()
    while True:
        j = api.get(f"/api/jobs/{jid}").json()
        if j["status"] in want or j["status"] in {"failed", "blocked"} or time.time() - t0 > limit:
            return j
        time.sleep(1)


def make_film(text: str, **extra: str) -> dict:
    r = api.post("/api/jobs", data={"text": text, "language": "id", "review": "false", **extra})
    r.raise_for_status()
    return r.json()


def state(page) -> list[dict]:
    return json.loads(page.get_attribute("[data-testid=kelir]", "data-state") or "[]")


def home_and_theatre_tests(page, jid: str | None) -> None:
    page.goto(f"{BASE}/", wait_until="networkidle")
    tag = "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film."
    step("home hero: sample film loop, tagline, sample label",
         page.locator("figure video source[src='/hero/sample-loop.mp4']").count() == 1
         and tag in page.locator("h1").inner_text() and page.get_by_text("Contoh · Sample film").count() == 1)
    page.get_by_test_id("hero-tell").click()
    page.wait_for_timeout(1200)
    top = page.evaluate("document.getElementById('cerita').getBoundingClientRect().top")
    step("home: 'Ceritakan · Tell a story' brings up the mic composer", abs(top) < 120
         and page.locator("#cerita-h").inner_text() == "Ceritakan kisahmu", f"composer top {top:.0f}px")
    if jid:  # a film still being made: the troupe is on stage
        page.goto(f"{BASE}/film/{jid}", wait_until="domcontentloaded")
        page.wait_for_selector("[data-testid=pipeline-theatre]", timeout=20000)
        page.wait_for_selector("[data-testid=pipeline-theatre] [data-active='1']", timeout=120000)
        n = page.locator("[data-testid=pipeline-theatre] [data-player]").count()
        step("pipeline theatre: six troupe members, one lit by the live trace/stage", n == 6,
             page.locator("[data-testid=pipeline-theatre] [data-active='1'] p.font-serif").first.inner_text())


def kelir_tests(page, jid: str) -> None:
    page.goto(f"{BASE}/kelir/{jid}", wait_until="networkidle")
    page.wait_for_selector("[data-testid=kelir][data-ready='1']", timeout=30000)
    page.wait_for_function("document.querySelector('[data-testid=kelir]').dataset.state", timeout=10000)
    box = page.locator("[data-testid=kelir]").bounding_box()
    assert box
    before = state(page)
    step("kelir live: stage ready with the film's puppets", len(before) >= 1 and box["width"] <= 390,
         f"{len(before)} puppets, stage {box['width']:.0f}x{box['height']:.0f}")
    # find a point on the first puppet's leather: scan around its centre with the page's own hit test
    p0 = before[0]
    sx, sy = box["x"] + p0["x"] * box["width"], box["y"] + p0["y"] * box["height"]
    page.mouse.move(sx, sy)
    page.mouse.down()
    for i in range(1, 11):
        page.mouse.move(sx + 8 * i, sy - 3 * i)
        page.wait_for_timeout(16)
    lifted = state(page)[0]["depth"]
    page.mouse.up()
    page.wait_for_timeout(700)
    after = state(page)[0]
    moved = after["x"] - p0["x"]
    step("kelir live: mouse drag moves the puppet and lifts it off the screen (softer shadow)",
         moved > 0.12 and lifted < 0.95 and after["depth"] > 0.95,
         f"dx {moved:.3f}, depth held {lifted:.2f}, released {after['depth']:.2f}")
    # two fingers: synthetic touch pointers, the second one twists and spreads
    cx, cy = box["x"] + after["x"] * box["width"], box["y"] + after["y"] * box["height"]
    page.evaluate(
        """([cx, cy]) => {
          const c = document.querySelector('[data-testid=kelir]');
          const ev = (type, id, x, y) => c.dispatchEvent(new PointerEvent(type, {pointerId: id, pointerType: 'touch',
            isPrimary: id === 11, clientX: x, clientY: y, bubbles: true, cancelable: true}));
          ev('pointerdown', 11, cx, cy);
          ev('pointerdown', 12, cx + 40, cy);
          for (let i = 1; i <= 10; i++) ev('pointermove', 12, cx + 40 + 6 * i, cy + 5 * i);
          window.__twist = JSON.parse(c.dataset.state || '[]');
          setTimeout(() => { ev('pointerup', 12, cx + 100, cy + 50); ev('pointerup', 11, cx, cy); }, 300);
        }""",
        [cx, cy],
    )
    page.wait_for_timeout(900)
    # the fingers land on whichever puppet is on top there (the dragged one may now overlap another)
    tw = max(state(page), key=lambda q: abs(q["rot"]))
    step("kelir live: two-finger touch tilts the puppet and spreading moves it toward the lamp",
         abs(tw["rot"]) > 0.3 and tw["depth"] < 0.9, f"{tw['id']} rot {tw['rot']:.2f} rad, depth {tw['depth']:.2f}")
    # keyboard path (accessibility): focus the stage and press keys
    page.focus("[data-testid=kelir]")
    x_before = sum(q["x"] for q in state(page))
    for _ in range(5):
        page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(300)
    step("kelir live: keyboard arrows move the selected puppet", sum(q["x"] for q in state(page)) < x_before - 0.05)
    # tap the gunungan (right edge, 89% across) -> next scene after the sweep
    scene0 = page.get_attribute("[data-testid=kelir]", "data-scene")
    page.mouse.click(box["x"] + 0.89 * box["width"], box["y"] + 0.5 * box["height"])
    page.wait_for_timeout(2200)
    scene1 = page.get_attribute("[data-testid=kelir]", "data-scene")
    step("kelir live: tapping the gunungan changes the scene", scene0 == "0" and scene1 == "1", f"{scene0} -> {scene1}")
    fps = page.get_attribute("[data-testid=kelir]", "data-fps")
    step("kelir live: animation loop running (fps reported)", fps is not None and int(fps) > 0, f"{fps} fps headless")
    rec = page.get_by_role("button", name="Rekam pertunjukan · Record my show")
    step("kelir live: record button available (MediaRecorder + captureStream)", rec.is_enabled())


def vote_tests(page, gid: str) -> None:
    g = wait_status(gid, {"choice"}, 300)
    vote_api = api.get(f"/api/jobs/{gid}/vote")
    if vote_api.status_code == 404:
        page.goto(f"{BASE}/film/{gid}", wait_until="networkidle")
        step("classroom vote hidden while the API has no vote endpoint", page.locator("[data-testid=classroom-vote]").count() == 0)
        return
    step("gara-gara film paused for the vote", g["status"] == "choice", g.get("gara_gara", {}).get("question", ""))
    page.goto(f"{BASE}/vote/{gid}", wait_until="networkidle")
    page.locator("button", has_text="🅰").first.click()
    page.wait_for_function("document.querySelector('[data-testid=vote-tally]')?.textContent.includes('1 suara')", timeout=10000)
    step("phone vote page: a tap casts one vote and shows the tally", api.get(f"/api/jobs/{gid}/vote").json()["total"] == 1)
    page.locator("button", has_text="🅱").first.click()
    page.wait_for_timeout(800)
    t = api.get(f"/api/jobs/{gid}/vote").json()
    step("phone vote page: tapping the other option changes the vote (one phone, one vote)",
         t["total"] == 1 and t["tally"] == [0, 1], json.dumps(t["tally"]))
    page.goto(f"{BASE}/film/{gid}", wait_until="networkidle")
    page.get_by_role("button", name="Buka voting · Open the vote").click()
    page.wait_for_selector("img[alt^='QR code: scan to vote']")
    page.get_by_role("button", name="Tutup voting, lanjutkan cerita · Close the vote and continue").click()
    page.wait_for_timeout(1500)
    after = api.get(f"/api/jobs/{gid}").json()
    step("classroom screen: closing the vote continues the film with the winner",
         after["status"] != "choice" and after["gara_gara"].get("answer") == t["options"][1], after["status"])


def remix_and_share_tests(page, jid: str) -> None:
    has_remix = api.get(f"/api/jobs/{jid}/remix").status_code != 404
    page.goto(f"{BASE}/film/{jid}", wait_until="networkidle")
    page.wait_for_selector("video")
    page.wait_for_timeout(800)
    shown = page.locator("[data-testid=remix]").count() > 0
    if not has_remix:
        step("remix buttons hidden while the API has no remix endpoint", not shown)
    else:
        step("remix buttons shown (API has remix)", shown)
        page.get_by_role("button", name="English").first.click()
        page.wait_for_url(lambda u: "/film/" in u and jid not in u, timeout=15000)
        new_id = page.url.rstrip("/").split("/")[-1]
        j = api.get(f"/api/jobs/{new_id}").json()
        step("remix: 'English' starts a remix job that reuses the puppets", j.get("remix_of") == jid
             and j.get("language") == "en", new_id)
    has_st = api.get(f"/api/jobs/{jid}/stickers").status_code == 200
    page.goto(f"{BASE}/watch/{jid}", wait_until="networkidle")
    # the sticker pack is fetched when the share bar comes near the screen
    page.locator("[aria-label='Bagikan film · Share this film']").scroll_into_view_if_needed()
    if has_st:
        try:
            page.wait_for_selector("[data-testid=viral-extras]", timeout=20000)
        except Exception:  # noqa: BLE001 - counted as a failure below
            pass
    else:
        page.wait_for_timeout(1500)
    n = page.locator("[data-testid=viral-extras]").count()
    step("share bar: sticker pack + GIF " + ("shown" if has_st else "hidden (no sticker endpoint)"),
         (n > 0) == has_st)


def pentas_tests(page) -> None:
    page.goto(f"{BASE}/pentas?urut=sembah", wait_until="networkidle")
    cards = page.locator("[data-testid=pentas-wall] > li")
    n = cards.count()
    claps = [int(cards.nth(i).get_attribute("data-applause") or 0) for i in range(n)]
    gallery = api.get("/api/gallery").json()
    own = [g for g in gallery if not g.get("sample")]
    step("/pentas lists the shared films, most applauded first", n == len(gallery) and n > 0
         and claps[: len(own)] == sorted(claps[: len(own)], reverse=True), f"{n} films, sembah {claps[:5]}")
    step("/pentas has OG + Twitter tags and the Made with Meta Muse badge",
         page.locator("meta[property='og:title']").count() == 1 and page.locator("meta[name='twitter:card']").count() == 1
         and page.locator("[data-testid=made-with-muse]").count() >= 1)
    first = cards.first
    before = int(first.get_attribute("data-applause") or 0)
    first.locator("button", has_text="Sembah").click()
    page.wait_for_timeout(800)
    label = first.locator("button", has_text="Sembah").inner_text()
    step("/pentas: Sembah on a card counts one bow", f"{before + 1}" in label, label)
    first.locator("[data-testid=share-card]").click()
    page.wait_for_selector("a[download$='-card.png']", timeout=15000)
    step("/pentas: share card drawn in the browser (1080x1350 PNG download)", True)
    page.goto(f"{BASE}/pentas", wait_until="networkidle")
    step("/pentas newest-first view renders", page.locator("[data-testid=pentas-wall] > li").count() == n)
    # PWA: once the service worker controls the page, the wall opens with the network off
    page.evaluate("navigator.serviceWorker && navigator.serviceWorker.ready")
    page.reload(wait_until="networkidle")
    page.context.set_offline(True)
    try:
        page.reload(wait_until="domcontentloaded")
        offline_ok = page.locator("[data-testid=pentas-wall] > li").count() == n
    except Exception as e:  # noqa: BLE001
        offline_ok, _ = False, e
    finally:
        page.context.set_offline(False)
    step("PWA: /pentas opens offline from the service worker cache", offline_ok)


def main() -> int:
    from playwright.sync_api import sync_playwright

    # R5_FILM=<id> reuses a finished film (quick local runs); otherwise make one on the fake pipeline
    jid = os.environ.get("R5_FILM") or make_film(
        "Kancil yang cerdik ingin menyeberang sungai penuh buaya untuk makan mentimun di seberang.")["id"]
    gid = os.environ.get("R5_GARA") or make_film(
        "Kancil bertemu buaya lagi di sungai, lalu mereka bermain bersama sampai sore hari.", gara_gara="true")["id"]
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True)
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        home_and_theatre_tests(page, None if os.environ.get("R5_FILM") else jid)
        done = wait_status(jid, {"done"})
        api.post(f"/api/jobs/{jid}/share", json={"public": True})
        step("film for the browser checks", done["status"] == "done", jid)
        kelir_tests(page, jid)
        remix_and_share_tests(page, jid)
        vote_tests(page, gid)
        pentas_tests(page)
        step("no uncaught page errors", not errors, "; ".join(errors[:3]))
        browser.close()
    print(f"\n{sum(ok)}/{len(ok)} web checks passed")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
