# Accessibility audit (axe-core)

Automated audit with **axe-core 4.12.1** (rules tagged wcag2a, wcag2aa, wcag21a, wcag21aa) in Chromium via Playwright,
run by `bash scripts/a11y_local.sh` on the fake Meta API (placeholder art). Each page is checked on a
phone (390x844) and a desktop (1280x800) screen in the night theme, then on the phone again in day mode
(its own colours); collapsible sections (the agent trace) are opened first.
Automated rules find about a third of real accessibility problems; a manual screen-reader pass is still
worth doing.

Run: 2026-11-07 00:52 WIB

| Page | Screen | Rules passed | Critical | Serious | Moderate | Minor |
|---|---|---|---|---|---|---|
| Home (`/`) | phone | 29 | 0 | 0 | 0 | 0 |
| Film (`film`) | phone | 30 | 0 | 0 | 0 | 0 |
| Watch (`watch`) | phone | 27 | 0 | 0 | 0 | 0 |
| Gallery (`gallery`) | phone | 26 | 0 | 0 | 0 | 0 |
| Kotak Wayang (`kotak`) | phone | 25 | 0 | 0 | 0 | 0 |
| Judge mode (`judge`) | phone | 26 | 0 | 0 | 0 | 0 |
| Teachers (`guru`) | phone | 25 | 0 | 0 | 0 | 0 |
| Pentas (`pentas`) | phone | 26 | 0 | 0 | 0 | 0 |
| Kelir Live (`kelir`) | phone | 28 | 0 | 0 | 0 | 0 |
| Vote (phone) (`vote`) | phone | 25 | 0 | 0 | 0 | 0 |
| Not found (`tidak-ada`) | phone | 25 | 0 | 0 | 0 | 0 |
| Home (`/`) | desktop | 29 | 0 | 0 | 0 | 0 |
| Film (`film`) | desktop | 30 | 0 | 0 | 0 | 0 |
| Watch (`watch`) | desktop | 27 | 0 | 0 | 0 | 0 |
| Gallery (`gallery`) | desktop | 26 | 0 | 0 | 0 | 0 |
| Kotak Wayang (`kotak`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Judge mode (`judge`) | desktop | 26 | 0 | 0 | 0 | 0 |
| Teachers (`guru`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Pentas (`pentas`) | desktop | 26 | 0 | 0 | 0 | 0 |
| Kelir Live (`kelir`) | desktop | 28 | 0 | 0 | 0 | 0 |
| Vote (phone) (`vote`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Not found (`tidak-ada`) | desktop | 25 | 0 | 0 | 0 | 0 |
| Home (`/`) | phone, day mode | 29 | 0 | 0 | 0 | 0 |
| Film (`film`) | phone, day mode | 30 | 0 | 0 | 0 | 0 |
| Watch (`watch`) | phone, day mode | 27 | 0 | 0 | 0 | 0 |
| Gallery (`gallery`) | phone, day mode | 26 | 0 | 0 | 0 | 0 |
| Kotak Wayang (`kotak`) | phone, day mode | 25 | 0 | 0 | 0 | 0 |
| Judge mode (`judge`) | phone, day mode | 26 | 0 | 0 | 0 | 0 |
| Teachers (`guru`) | phone, day mode | 25 | 0 | 0 | 0 | 0 |
| Pentas (`pentas`) | phone, day mode | 26 | 0 | 0 | 0 | 0 |
| Kelir Live (`kelir`) | phone, day mode | 28 | 0 | 0 | 0 | 0 |
| Vote (phone) (`vote`) | phone, day mode | 25 | 0 | 0 | 0 | 0 |
| Not found (`tidak-ada`) | phone, day mode | 25 | 0 | 0 | 0 | 0 |

## Findings

No violations on any page.

Not counted above: axe's "needs review" items, which it cannot decide automatically (for example text
contrast over a picture). Re-run after UI changes: `cd web && npm run build && cd .. && bash scripts/a11y_local.sh`
(exit code 1 on any serious or critical violation).
