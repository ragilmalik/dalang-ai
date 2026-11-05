# Web performance (phone, 390x844 @2x, local production build)

Measured by `scripts/web_perf.py` with Playwright + Chromium against `next start` and the fake-API backend
on the sandbox (no network throttling, so read the numbers relative to each other). Image flags: over
300 KB, or more than 2.5x wider than shown.

| Page | DOMContentLoaded | Load | LCP | Transferred | Images (lazy) | Flags |
|---|---|---|---|---|---|---|
| `/` | 64 ms | 328 ms | 232 ms | 523 KB | 1 (0) | none |
| `/gallery` | 112 ms | 293 ms | 332 ms | 764 KB | 3 (3) | none |
| `/kotak` | 79 ms | 390 ms | 516 ms | 515 KB | 0 (0) | none |
| `/watch/JR6ibkCs` | 141 ms | 536 ms | 360 ms | 600 KB | 0 (0) | none |

Bytes by type: `/` document 14 KB, fetch 20 KB, image 1 KB, other 0 KB, script 471 KB, stylesheet 15 KB; `/gallery` document 18 KB, fetch 20 KB, image 236 KB, other 0 KB, script 472 KB, stylesheet 15 KB; `/kotak` document 12 KB, fetch 16 KB, other 0 KB, script 471 KB, stylesheet 15 KB; `/watch/JR6ibkCs` document 20 KB, fetch 16 KB, image 72 KB, other 0 KB, script 476 KB, stylesheet 15 KB
