# TODO

What is open right now. The long product checklist (every feature, done or not) is in `docs/TODO.md`.

Status legend: [x] done · [ ] open · [!] waiting on me (Malik)

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
- [ ] Fresh security sweep on a new export, then push to github.com/ragilmalik/dalang-ai
- [ ] Upload the finished files to Google Drive, folder "Meta Hackathon - Dalang AI" (not shared publicly)
- [ ] Full HANDOFF.md

## Waiting on me
- [!] Deploy, set `PUBLIC_BASE_URL`, then make the QR (`scripts/make_qr.py`)
- [!] Real family sessions or a cultural review, with consent, before any quote goes on the site or in the submission
- [!] Submit the hackathon form (the official deadline, Nov 5 09:00 WIB, has passed)
