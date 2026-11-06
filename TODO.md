# TODO

What is open right now. The long product checklist (every feature, done or not) is in `docs/TODO.md`.

Status legend: [x] done · [ ] open · [!] waiting on me (Malik)

## Polish and weak spots (2026-11-06, second pass)
- [x] Audit every page at 375 and 1440 px (a one-off Playwright script I keep outside the repo): console errors, failed requests,
      overflow, tap targets under 44 px, images without size, bytes, LCP, layout shift (CLS)
- [x] Layout shift: footer jumped when client pages filled in (film CLS 0.78 desktop, 0.32 phone); fixed with a
      screen-high `main` and `scrollbar-gutter: stable`. Home hero columns now `minmax(0, ...)` so the font load
      can't move the film (was 0.20). Every page now under 0.1
- [x] Gallery and Pentas weight: 800 px WebP cards (`api/thumbs.py`, made once per film) with `srcset`; gallery
      1.2 MB -> about 0.5 MB, Pentas 1.0-1.2 MB -> about 0.5 MB
- [x] Tap targets: small buttons, footer links, logo, judge links and "Every step" now 44 px tall
- [x] Puppet pictures have width and height (no reflow)
- [x] Day mode paints the phone's browser bar light too (`meta theme-color` follows the theme)
- [x] axe now also checks day mode on a phone (its own colours were never audited)
- [x] tests/test_thumbs.py (6 tests); ruff, mypy, tsc, eslint clean; next build OK
- [x] axe: 33 page checks, 0 violations
- [x] Recorder double-tap check fired the second tap from Python, which can take longer than the 1.2 s guard on a
      busy machine; it now taps inside the page in the first frame the ring shows
- [x] Wording pass: `scripts/voice_check.py` scans every doc, code comment and docstring for AI-sounding words, notes
      written for a coding tool and dashes, and exits 1 until it finds nothing. It finds nothing now, and
      `tests/test_voice_check.py` keeps it that way
- [x] e2e smoke 29/29 and browser 30/30, pytest 546 (95% of `api/`), facts.json updated
- [x] Docs, commit, secret sweep, push to GitHub
- [ ] Refresh the private Drive folder with this release

## Smoother site (2026-11-06, first pass)
- [x] Research: Next.js 16.4 view transitions guide, web.dev motion and reduced-motion, Google "Building for kids",
      BBC GEL voice principles
- [x] Page transitions (`app/template.tsx`), header anchored, reduced motion respected
- [x] Poster to player morph (gallery, Pentas -> watch)
- [x] Loading skeletons for gallery and Pentas (`components/CardsSkeleton.tsx`)
- [x] Recorder: start/stop notes and buzz, 90 s ring, double-tap guard, screen reader status, no double start
- [x] Progress and vote bars on `scaleX`
- [x] tsc 0, eslint 0
- [x] next build + e2e: smoke 29/29, browser 30/30 (4 new checks: header anchor, poster morph, recorder guard, recorder stop)
- [x] axe a11y: 22 page checks, 0 violations
- [x] pytest 531 passed (no backend change), ruff, mypy (69 files), facts check agrees
- [x] Recorder ring checked by eye at 390 px; no screenshot in docs shows a changed screen at rest
- [x] Commit locally
- [x] Push to GitHub after a fresh secret sweep (same export flow as cecf771)

## Final checks (Nov 6)
- [x] e2e on the fake API: smoke 29/29, browser 26/26 (`scripts/e2e_local.sh`)
- [x] Accessibility: axe 22 page checks, 0 violations (`scripts/a11y_local.sh`)
- [x] Judge page no longer says "my cultural rules"
- [x] Docs: no made-up link, no pointer to the removed testimonials file, sample voice called synthetic, tutorial
      matches the no-key behaviour (new films refused until a key is set, or `FAKE_META=true` for test mode)
- [x] G9: self-hosted `next start` gzips JS; the progress stream sends `Cache-Control: no-transform` and still streams
- [x] G10: a recording sent for a film that failed stays on the device (IndexedDB, up to 6 hours, cleared when a film
      is done) so it can be sent again without re-recording
- [x] Click-through of 16 pages at 375 px (dark and light) and 1440 px on the fake API: no console errors, no failed
      requests, no overflow, no broken links or images
- [x] Full pytest with coverage: 527 passed, 95%
- [x] ruff, mypy, eslint, tsc, next build, facts check, slop check: clean

## Media on the live models (Nov 6)
- [x] Start the app on the live Meta API (`work/live/RUN_LIVE.sh`, spend cap $14 total; recording via `work/live/demo_live.sh`)
- [x] Re-record the demo video (2:57, 1920x1080, captions, -16.7 LUFS, synthetic narrator labelled) and both teasers;
      launch clips and thumbnail too
- [x] Re-take the UI screenshots (28), README crops, agent trace, Kotak Wayang and printable puppet from live films
- [x] Check every shot by eye; fixed the close card's placeholder line, dead air under the app shots, an unmeasured
      claim in the narration, and a Muse Wonder plan thrown away for one out-of-range angle (now clamped)
- [x] Full checks again after these changes: pytest 531 passed (95%), e2e 29/29 + 26/26, axe 22/0, ruff, mypy, eslint, tsc, facts

## Release
- [x] Fresh security sweep on a new export (gitleaks 0, key suffix 0, no file over 50 MB), pushed to
      github.com/ragilmalik/dalang-ai as a second commit on top of the first release (no history rewritten)
- [x] Upload the finished files to Google Drive, folder "Meta Hackathon - Dalang AI" (private, not shared)
- [x] HANDOFF.md: state, what is real and what is synthetic, links, gotchas

## Waiting on me
- [!] Watch the demo video once, then upload it to YouTube (unlisted) with `docs/demo/dalang-ai-demo.srt`
- [!] Optional: my own voice-over or a consented child recording (`docs/demo/real/README.md`), a native Javanese check
- [!] Deploy, set `PUBLIC_BASE_URL`, then make the QR (`scripts/make_qr.py`)
- [!] Real family sessions or a cultural review, with consent, before any quote goes on the site or in the submission
- [!] Submit the hackathon form (the official deadline, Nov 5 09:00 WIB, has passed)
