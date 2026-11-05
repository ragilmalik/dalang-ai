# Accessibility audit (axe-core)

Automated audit with **axe-core 4.12.1** (rules tagged wcag2a, wcag2aa, wcag21a, wcag21aa) in Chromium via Playwright,
run by `bash scripts/a11y_local.sh` on the fake Meta API (placeholder art). Each page is checked on a
phone (390x844) and a desktop (1280x800) screen; collapsible sections (the agent trace) are opened first.
Automated rules find about a third of real accessibility problems; a manual screen-reader pass is still
worth doing.

Run: 2026-11-04 08:23 WIB

| Page | Screen | Rules passed | Critical | Serious | Moderate | Minor |
|---|---|---|---|---|---|---|
| Home (`/`) | phone | 28 | 0 | 0 | 0 | 0 |
| Film (`film`) | phone | 30 | 0 | 0 | 0 | 0 |
| Watch (`watch`) | phone | 26 | 0 | 0 | 0 | 0 |
| Gallery (`gallery`) | phone | 25 | 0 | 0 | 0 | 0 |
| Kotak Wayang (`kotak`) | phone | 24 | 0 | 0 | 0 | 0 |
| Judge mode (`judge`) | phone | 29 | 0 | 0 | 0 | 0 |
| Teachers (`guru`) | phone | 24 | 0 | 0 | 0 | 0 |
| Pentas (`pentas`) | phone | 25 | 0 | 0 | 0 | 0 |
| Kelir Live (`kelir`) | phone | 27 | 0 | 0 | 0 | 0 |
| Vote (phone) (`vote`) | phone | 24 | 0 | 0 | 0 | 0 |
| Not found (`tidak-ada`) | phone | 24 | 0 | 0 | 0 | 0 |
| Home (`/`) | desktop | 28 | 0 | 0 | 0 | 0 |
| Film (`film`) | desktop | 30 | 0 | 0 | 0 | 0 |
| Watch (`watch`) | desktop | 26 | 0 | 0 | 0 | 0 |
| Gallery (`gallery`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Kotak Wayang (`kotak`) | desktop | 24 | 0 | 0 | 0 | 0 |
| Judge mode (`judge`) | desktop | 29 | 0 | 0 | 0 | 0 |
| Teachers (`guru`) | desktop | 24 | 0 | 0 | 0 | 0 |
| Pentas (`pentas`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Kelir Live (`kelir`) | desktop | 27 | 0 | 0 | 0 | 0 |
| Vote (phone) (`vote`) | desktop | 24 | 0 | 0 | 0 | 0 |
| Not found (`tidak-ada`) | desktop | 24 | 0 | 0 | 0 | 0 |

## Findings

No violations on any page.

Not counted above: axe's "needs review" items, which it cannot decide automatically (for example text
contrast over a picture). Re-run after UI changes: `cd web && npm run build && cd .. && bash scripts/a11y_local.sh`
(exit code 1 on any serious or critical violation).
