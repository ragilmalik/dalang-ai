# Web performance, pages added Nov 1-2

Measured with `python web/e2e/r5_perf.py` on a local production build (`next start`, fake-Meta API), Chromium
headless, 390x844 phone viewport at 2x, cold cache, service worker blocked, median of 3 loads. Targets: home LCP
under 1500 ms, CLS under 0.02 on every page.

Nov 4 (measured 2026-11-04 01:28 UTC, submission day):

| Page | Path | LCP | CLS | DOMContentLoaded | Transferred |
|---|---|---|---|---|---|
| Home | `/` | 680 ms | 0.000 | 276 ms | 805 KB |
| Pentas | `/pentas` | 692 ms | 0.000 | 554 ms | 791 KB |
| Pentas, most applauded | `/pentas?urut=sembah` | 572 ms | 0.000 | 306 ms | 791 KB |
| Kelir Live | `/kelir/[id]` | 740 ms | 0.000 | 452 ms | 972 KB |
| Watch | `/watch/[id]` | 948 ms | 0.000 | 1175 ms | 805 KB |

Both targets are met. The home bundle is the same as on Nov 3 (528 KB raw, 159 KB gzipped, the same as the plain
/guru page, so it's the shared React and Next.js code). This run shared the machine with a demo video encode and
other jobs, which is why the numbers are higher than Nov 3. These are loopback numbers, so they show page weight and
layout stability; a real phone network will be slower.

Nov 3 (measured 2026-11-03 05:03 UTC, after the cheap-phone changes):

| Page | Path | LCP | CLS | DOMContentLoaded | Transferred |
|---|---|---|---|---|---|
| Home | `/` | 452 ms | 0.000 | 350 ms | 801 KB |
| Pentas | `/pentas` | 580 ms | 0.000 | 393 ms | 705 KB |
| Pentas, most applauded | `/pentas?urut=sembah` | 408 ms | 0.000 | 221 ms | 705 KB |
| Kelir Live | `/kelir/[id]` | 340 ms | 0.006 | 208 ms | 697 KB |
| Watch | `/watch/[id]` | 300 ms | 0.006 | 301 ms | 697 KB |

Both targets are met. The home page is the same size as on Nov 2, so I don't count the faster numbers as a speed-up:
the machine was less busy during this run. The Nov 3 changes were for cheap phones (Kelir Live idles at about 30 fps,
the film page stops polling when the film is done, no hero loop on Data Saver, 2G or 3G).

On a throttled slow 3G profile (400 ms round trip, 500 kbit/s, 4x CPU slowdown), measured before the Nov 3 web
changes: home 4.7 s and 725 KB (mostly the composer's JavaScript; its LCP element is the 5 KB poster), watch 2.3 s,
Pentas 1.3 s.

After the Nov 2 redesign (measured 2026-11-02 07:40 UTC):

| Page | Path | LCP | CLS | DOMContentLoaded | Transferred |
|---|---|---|---|---|---|
| Home | `/` | 1108 ms | 0.000 | 984 ms | 799 KB |
| Pentas | `/pentas` | 1520 ms | 0.000 | 758 ms | 787 KB |
| Pentas, most applauded | `/pentas?urut=sembah` | 1600 ms | 0.000 | 572 ms | 788 KB |
| Kelir Live | `/kelir/[id]` | 892 ms | 0.000 | 651 ms | 968 KB |
| Watch | `/watch/[id]` | 1656 ms | 0.000 | 950 ms | 801 KB |

Both targets were met. Pentas and Watch got 0.4 to 0.7 s slower to their largest paint with the redesign, and I
haven't looked into why yet. There's no layout shift on any page.

Before the redesign (2026-11-01 19:04 UTC): home 1068 ms, Pentas 788 ms, Pentas most applauded 1044 ms, Kelir Live
864 ms, Watch 1236 ms, CLS 0.000 everywhere.

Local loopback numbers: they show the page's own weight and layout stability, not a phone network.
