"""Phone-size performance check of the pages added Nov 1-2 (Kelir Live, vote, Pentas) in a local production build (Playwright + Chromium).

    python web/e2e/r5_perf.py http://127.0.0.1:3005 [film_id] [--out docs/WEB_PERF_R5.md]

Per page: largest contentful paint (LCP), cumulative layout shift (CLS, from layout-shift entries without recent
input), DOMContentLoaded and bytes. Targets: LCP < 1500 ms on the home page, CLS < 0.02 everywhere.
Each page is loaded three times in a fresh context (cold cache) and the median is kept. Exit 1 if a target fails.
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_path import launch_kwargs  # noqa: E402

JS = """() => new Promise(res => {
  let lcp = 0, cls = 0;
  new PerformanceObserver(l => { for (const e of l.getEntries()) lcp = e.startTime; })
    .observe({type: 'largest-contentful-paint', buffered: true});
  new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) cls += e.value; })
    .observe({type: 'layout-shift', buffered: true});
  setTimeout(() => {
    const n = performance.getEntriesByType('navigation')[0];
    const bytes = performance.getEntriesByType('resource').reduce((s, r) => s + (r.transferSize || 0), n.transferSize || 0);
    res({lcp, cls, dcl: n.domContentLoadedEventEnd, bytes});
  }, 1500);
})"""


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else "http://127.0.0.1:3005"
    film = args[1] if len(args) > 1 else None
    out = None
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    pages = [("Home", "/"), ("Pentas", "/pentas"), ("Pentas, most applauded", "/pentas?urut=sembah")]
    if film:
        pages += [("Kelir Live", f"/kelir/{film}"), ("Watch", f"/watch/{film}")]
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
        for name, path in pages:
            runs = []
            for _ in range(3):
                ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                          service_workers="block")
                page = ctx.new_page()
                page.goto(base + path, wait_until="load")
                runs.append(page.evaluate(JS))
                ctx.close()
            med = {k: statistics.median(r[k] for r in runs) for k in ("lcp", "cls", "dcl", "bytes")}
            rows.append((name, path, med))
            print(f"{name:26s} LCP {med['lcp']:6.0f} ms  CLS {med['cls']:.3f}  DCL {med['dcl']:6.0f} ms  "
                  f"{med['bytes'] / 1024:6.0f} KB", flush=True)
        browser.close()
    fails = [n for n, path, m in rows if m["cls"] >= 0.02 or (path == "/" and m["lcp"] >= 1500)]
    if out:
        lines = ["# Web performance, pages added Nov 1-2", "",
                 f"Measured {time.strftime('%Y-%m-%d %H:%M %Z')} with `python web/e2e/r5_perf.py` on a local production "
                 "build (`next start`, fake-Meta API), Chromium headless, 390x844 phone viewport at 2x, cold cache, "
                 "service worker blocked, median of 3 loads. Targets: home LCP < 1500 ms, CLS < 0.02 on every page.", "",
                 "| Page | Path | LCP | CLS | DOMContentLoaded | Transferred |", "|---|---|---|---|---|---|"]
        for n, path, m in rows:
            shown = path.replace(film, "[id]") if film else path
            lines.append(f"| {n} | `{shown}` | {m['lcp']:.0f} ms | {m['cls']:.3f} | {m['dcl']:.0f} ms | "
                         f"{m['bytes'] / 1024:.0f} KB |")
        lines += ["", "All targets met." if not fails else f"Over target: {', '.join(fails)}.", "",
                  "Local loopback numbers: they show the page's own weight and layout stability, not a phone network."]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS perf targets" if not fails else f"FAIL perf: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
