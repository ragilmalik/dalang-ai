"""Lighthouse-style check of the website on a phone-sized screen, with Playwright (no Lighthouse install needed).

    python scripts/web_perf.py http://127.0.0.1:3000            # app must be running; writes docs/WEB_PERF.md
    python scripts/web_perf.py http://127.0.0.1:3000 --shot docs/screenshots/6-gallery.png

For each page: time to DOMContentLoaded and load, largest contentful paint, bytes transferred (by type), and every
image with its file size, natural size and shown size. An image is flagged when it is over 300 KB or more than
2.5x wider than it is shown (it should be resized or compressed). Exit code 1 if any page has a flag.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_path import launch_kwargs  # noqa: E402

MAX_IMG_BYTES = 300_000
MAX_OVERSIZE = 2.5
LCP_JS = """() => new Promise(res => {
  let v = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) v = e.startTime; })
    .observe({type: 'largest-contentful-paint', buffered: true});
  setTimeout(() => res(v), 300);
})"""
IMGS_JS = """() => [...document.images].map(i => ({src: i.currentSrc || i.src, nw: i.naturalWidth,
  shown: Math.round(i.getBoundingClientRect().width * devicePixelRatio), lazy: i.loading === 'lazy'}))"""


def measure(page, url: str) -> dict:
    sizes: dict[str, int] = {}
    kinds: dict[str, int] = {}

    def on_response(r):
        try:
            n = len(r.body())
        except Exception:  # noqa: BLE001 - streamed or aborted responses have no body
            return
        sizes[r.url] = n
        k = r.request.resource_type
        kinds[k] = kinds.get(k, 0) + n

    page.on("response", on_response)
    t0 = time.time()
    page.goto(url, wait_until="load")
    page.wait_for_load_state("networkidle")
    nav = page.evaluate("() => { const n = performance.getEntriesByType('navigation')[0];"
                        " return {dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd}; }")
    lcp = page.evaluate(LCP_JS)
    imgs = page.evaluate(IMGS_JS)
    page.remove_listener("response", on_response)
    flags = []
    for im in imgs:
        im["bytes"] = sizes.get(im["src"], 0)
        if im["bytes"] > MAX_IMG_BYTES:
            flags.append(f"{im['src'].split('/')[-1][:50]}: {im['bytes'] // 1024} KB")
        if im["shown"] and im["nw"] > im["shown"] * MAX_OVERSIZE:
            flags.append(f"{im['src'].split('/')[-1][:50]}: {im['nw']} px wide, shown at {im['shown']} px")
    return {"url": url, "dcl_ms": round(nav["dcl"]), "load_ms": round(nav["load"]), "lcp_ms": round(lcp),
            "wall_s": round(time.time() - t0, 2), "bytes": sum(kinds.values()), "by_type": kinds,
            "images": imgs, "flags": flags}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--out", default=str(ROOT / "docs" / "WEB_PERF.md"))
    ap.add_argument("--shot", help="also save a phone screenshot of the gallery here")
    a = ap.parse_args(argv)
    import httpx
    from playwright.sync_api import sync_playwright
    base = a.base.rstrip("/")
    gallery = httpx.get(f"{base}/api/gallery", timeout=30, trust_env=False).json()
    pages = ["/", "/gallery", "/kotak"] + ([f"/watch/{gallery[0]['id']}"] if gallery else [])
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                  has_touch=True)
        for path in pages:
            page = ctx.new_page()
            page.goto(base + path, wait_until="load")  # warm-up: Next compiles nothing in production, but caches
            page.close()
            page = ctx.new_page()
            results.append(measure(page, base + path))
            if a.shot and path == "/gallery":
                page.screenshot(path=a.shot, full_page=False)
            page.close()
        browser.close()
    lines = ["# Web performance (phone, 390x844 @2x, local production build)", "",
             "Measured by `scripts/web_perf.py` with Playwright + Chromium against `next start` and the fake-API backend",
             "on the sandbox (no network throttling, so read the numbers relative to each other). Image flags: over",
             f"{MAX_IMG_BYTES // 1000} KB, or more than {MAX_OVERSIZE}x wider than shown.", "",
             "| Page | DOMContentLoaded | Load | LCP | Transferred | Images (lazy) | Flags |", "|---|---|---|---|---|---|---|"]
    for r in results:
        path = r["url"].replace(base, "") or "/"
        n_lazy = sum(1 for i in r["images"] if i["lazy"])
        lines.append(f"| `{path}` | {r['dcl_ms']} ms | {r['load_ms']} ms | {r['lcp_ms']} ms | {r['bytes'] // 1024} KB "
                     f"| {len(r['images'])} ({n_lazy}) | {'; '.join(r['flags']) or 'none'} |")
    lines += ["", "Bytes by type: " + "; ".join(
        f"`{(r['url'].replace(base, '') or '/')}` " + ", ".join(f"{k} {v // 1024} KB" for k, v in sorted(r["by_type"].items()))
        for r in results), ""]
    Path(a.out).write_text("\n".join(lines))
    print(json.dumps([{k: r[k] for k in ("url", "dcl_ms", "load_ms", "lcp_ms", "bytes", "flags")} for r in results], indent=1))
    return 1 if any(r["flags"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
