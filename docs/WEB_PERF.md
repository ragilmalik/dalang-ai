# Web performance (phone, 390x844 @2x, local production build)

Measured by `scripts/web_perf.py` with Playwright + Chromium against `next start` and the fake-API backend
on my dev box (no network throttling, so read the numbers relative to each other). Image flags: over
300 KB, or more than 2.5x wider than shown.

| Page | DOMContentLoaded | Load | LCP | Transferred | Images (lazy) | Flags |
|---|---|---|---|---|---|---|
| `/` | 64 ms | 328 ms | 232 ms | 523 KB | 1 (0) | none |
| `/gallery` | 112 ms | 293 ms | 332 ms | 764 KB | 3 (3) | none |
| `/kotak` | 79 ms | 390 ms | 516 ms | 515 KB | 0 (0) | none |
| `/watch/JR6ibkCs` | 141 ms | 536 ms | 360 ms | 600 KB | 0 (0) | none |

Bytes by type: `/` document 14 KB, fetch 20 KB, image 1 KB, other 0 KB, script 471 KB, stylesheet 15 KB; `/gallery` document 18 KB, fetch 20 KB, image 236 KB, other 0 KB, script 472 KB, stylesheet 15 KB; `/kotak` document 12 KB, fetch 16 KB, other 0 KB, script 471 KB, stylesheet 15 KB; `/watch/JR6ibkCs` document 20 KB, fetch 16 KB, image 72 KB, other 0 KB, script 476 KB, stylesheet 15 KB

## 2026-11-06: layout shift and card weight

The table above is from before the 800 px WebP poster cards (`api/thumbs.py`). On Nov 6 I measured every page at
375 px and 1440 px with headless Chromium against `next start` and the fake-API backend, again with no throttling.

| Measure | Before | After |
|---|---|---|
| Gallery, desktop, bytes transferred | 1222 KB | about 492 KB |
| Pentas, desktop, bytes transferred | 1209 KB | about 517 KB |
| Film page layout shift (CLS), desktop | 0.784 | 0.051 |
| Film page layout shift, phone | 0.321 | 0 |
| Home layout shift, desktop | 0.204 | 0 |
| Vote page layout shift, desktop | 0.181 | 0.087 |
| Horizontal overflow at 375 and 1440 px | none | none |

Every page now shifts less than 0.1. LCP moved between 0.3 s and 2.3 s from run to run on my shared dev box, so I
don't read anything into it here. The failed requests in those runs were cancelled prefetches and the 404 page's
own expected 404.
