# Test report

## Where things stand (numbers from `docs/facts.json`)

| Check | Result |
|---|---|
| pytest (`pytest -q`, fake Meta API) | <!-- facts:tests -->520<!-- /facts --> tests pass, <!-- facts:coverage -->96%<!-- /facts --> line coverage of `api/` |
| Full-stack e2e (`bash scripts/e2e_local.sh`) | <!-- facts:e2e -->27/27<!-- /facts --> steps |
| Browser checks of the newest screens (`web/e2e/r5_ui.py`, 390 px phone) | 25/25 |
| axe-core audit (`bash scripts/a11y_local.sh`) | <!-- facts:a11y -->22<!-- /facts --> page checks, 0 violations ([ACCESSIBILITY.md](ACCESSIBILITY.md)) |
| Home page largest paint (`web/e2e/r5_perf.py`, local production build) | under the 1.5 s target: 680 ms on Nov 4 (shared machine), 452 ms on Nov 3, 1108 ms on Nov 2 ([WEB_PERF_R5.md](WEB_PERF_R5.md)) |
| Nov 3 after-checks (headers, titles, noindex, console, mic message, offline page, odd upload, one Sembah) | 21/21 |
| Nov 4 after-checks (judge page, API docs link, missing film, home retry, kept story, gallery empty state) | 12/12 |
| Demo video | <!-- facts:demo_length -->2:58<!-- /facts -->, 1920x1080, -16.8 LUFS, re-recorded on Nov 4 on the current site |

The sections below are the dated runs, oldest first.

## First full run: 2026-10-30, 05:31-05:35 WIB

Fresh `.venv` (Python 3.12.15), Node 22.23.3, ffmpeg 7.1.5, Next.js 16.4.3; fake Meta API (no key).
Script: `work/final.sh` in my working folder outside the repo (same commands as `.github/workflows/ci.yml`).

| Check | Command | Result |
|---|---|---|
| Python lint | `ruff check api scripts tests docs/architecture.py` | **exit 0** |
| Python types | `mypy api scripts` | **Success: no issues found in 31 source files** |
| Tests | `pytest -q tests` | **38 passed** in 48.4 s |
| Key check self-test | `python scripts/check_keys.py --self-test` | **All 7 checks passed** |
| Web types / lint | `npx tsc --noEmit` / `npx eslint .` | **exit 0 / exit 0** |
| Web build | `npx next build` | **exit 0**; routes `/`, `/film/[id]`, `/gallery`, `/watch/[id]`, `/icon.svg` |
| Full-stack smoke (through Next, audio upload) | `python scripts/smoke_test.py http://127.0.0.1:3005` | **13/13 passed**; 59.4 s film, cost meter $0.1806, 16:9 5028 KB + 9:16 4531 KB |
| Output file | `ffprobe` | h264 1280x720 + aac, 59.33 s |
| Music bed + narration level (12-18 s) | `ffmpeg -af volumedetect` | mean -20.6 dB, max -4.3 dB (no clipping) |
| Screenshots | `python scripts/screenshots.py` (Chromium 156, 390x844 @2x) | 4 screens + demo.gif + poster.jpg in `docs/screenshots/` |
| Docker | `docker build` | **not run here**: no Docker in the sandbox. The CI `docker` job builds both images and runs the smoke test against the container on first push. |

New tests this round (`tests/test_pipeline.py`, 17 tests): safety screen blocks war, political and medical
stories with a friendly message and never reaches the script writer; lakon retries once after invalid JSON,
then fails gracefully (job `failed`, stage marked); verify agent redraws up to 2 times then keeps the last
image and flags it, and accepts after one redraw; cost guard stops a job before animation; transcript-hash
cache hit makes no model call; DEMO_MODE replays the saved film when a Meta call fails, and without it the
failure is reported; Javanese audio goes to Muse Spark 1.2 (Voice Transcribe not called); uploaded and
converted audio are deleted after transcription (Javanese and Indonesian); more than 6 scenes or 4
characters rejected; unshared films stay out of the gallery, sharing then unsharing works, gallery has no
transcript.

Bugs found this round: a stale `next-server` from an earlier run served an old build (page showed "This
page couldn't load"; fixed by stopping it, scripts now kill `next-server`); the SAM fallback swallowed the
budget error (now re-raised); missing favicon 404 (added `app/icon.svg`); storyboard is now shown above
the stage list.

---

## Earlier run: 2026-10-30, 03:20-03:40 WIB
In a fresh Linux sandbox (Python 3.12.15, Node 22.23.3, ffmpeg 7.1.5),
dependencies installed from scratch with `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
No Meta key: every Meta call was answered by the built-in fake Meta API (`api/fake_meta.py`), which runs the
real client code (request building, retries, SSE parsing with Meta's `meta-sam-parser`, cost metering).

## Summary

| Check | Command | Result |
|---|---|---|
| Python lint | `ruff check api scripts tests docs/architecture.py` | **All checks passed** |
| Python types | `mypy api scripts` | **Success: no issues found in 30 source files** |
| Unit + integration tests | `pytest -v tests` | **21 passed** in 24.9 s |
| Key-check script (self-test) | `python scripts/check_keys.py --self-test` | **All 7 checks passed** |
| Web types | `cd web && npx tsc --noEmit` | **exit 0** |
| Web lint | `npx eslint .` | **exit 0, 0 problems** |
| Web production build | `npx next build` | **exit 0**; routes `/`, `/film/[id]`, `/gallery`, `/watch/[id]` |
| Full-stack smoke test (through the website, like a phone) | `python scripts/smoke_test.py http://127.0.0.1:3005` | **13/13 passed** |
| Offline film render (demo seed) | `python scripts/demo_seed.py` | **done**: 59 s film, 16:9 + 9:16, Indonesian narration, cost meter $0.180, 123 s wall time |

## pytest (first 21 tests)

* `test_api_e2e.py`: health; empty/invalid requests rejected (400); **war story blocked by the safety screen**;
  **full flow** (text story → 4 stages done → storyboard with 5 scenes and 2 SAM cut-outs → the verify agent
  redrew one backdrop → edit a line + repaint scene 1 → approve → film done → H.264 1280x720 + AAC verified with
  ffmpeg → cost under the cap → not in gallery until shared → shared → in gallery); **SSE against a real uvicorn
  server** (incremental events, stream ends at review); media path traversal blocked; SAM endpoint was exercised.
* `test_meta_client.py`: structured output parsed and metered; Muse Image PNG at the requested size and $0.01
  metered; **SAM stream → meta-sam-parser → mask round trip**; ASR multipart; **exact request shapes vs the docs**
  (URLs, model ids, `response_format.json_schema`, `tool_enablement` keys, Bearer auth); unknown image field
  rejected (400) like the real API; **budget guard** stops spending.
* `test_engine.py`: pixel-width caption wrapping; keyframe interpolation and facing; frame sizes for 16:9 and 9:16.
* `test_schemas.py`: sample script valid; unknown characters dropped and staging filled; fewer than 4 scenes
  rejected; motion-plan bounds enforced.

## Full-stack smoke test output (03:40 run)

```
PASS landing page 200
PASS health via Next proxy
PASS job created from audio upload          (3 s Opus/WebM, like a phone's recorder)
PASS SSE streams incrementally through Next 9 events, first at 0.0s, last at 4.1s
PASS transcript from ASR
PASS storyboard has stills
PASS film page renders
PASS film finished                          59.4 s, cost $0.1806
PASS landscape video served                 4931 KB
PASS vertical video served                  4433 KB
PASS watch page hidden before share
PASS watch page public after share, with OG tags
PASS gallery lists the film
13/13 passed
```

## Visual check

Frames from the rendered film were inspected: title card with gunungan, each scene with puppets on their
marks, subtitles inside the frame in both 16:9 and 9:16 (an earlier overflow in 9:16 was fixed by
measuring text width), gunungan wipe between scenes, end card with the moral.

## Bugs found and fixed during testing

1. 9:16 subtitles ran off the screen → pixel-width wrapping (`engine.wrap_px`).
2. SSE stream never ended during storyboard review → stream now closes at review; the browser reconnects.
3. Fake safety screen read the system prompt and blocked every story → screens only the user's story.
4. Placeholder art differed between runs (Python hash seed) → stable CRC32 seed.
5. `Image.save()` return value used as a path in `puppet.py` → fixed; mypy now clean.

## Not covered here (needs me)

* Live calls to Meta: run `python scripts/check_keys.py` with the real key (about $0.03), then make one film.
* Phone over https: start `cloudflared tunnel --url http://localhost:3000` and open the address on a phone
  (the sandbox cannot run a browser or expose a public URL). The layout is responsive (Tailwind, `max-w`,
  `sm:` breakpoints, viewport meta), and the microphone requires https or localhost.

## 2026-10-31 09:15 WIB
ruff 0 | mypy clean (45 files) | pytest 100 passed | eslint 0 | tsc 0 | next build 0 | e2e 21/21 | go_live dry run 8/8

## 2026-10-31 11:50 WIB
ruff 0 | mypy clean (45) | pytest 112 passed | eslint 0 | tsc 0 | next build 0 | e2e 22/22 | bandit -ll clean | npm/pip audit 0

## 2026-10-31 14:40 WIB
ruff 0 | mypy clean (51) | pytest 132 passed | coverage 93% | eslint 0 | tsc 0 | next build 0 | bandit 0 | e2e 23/23

## 2026-11-01 05:00 WIB (polish pass 3)
ruff 0 | mypy clean (53 files) | pytest 136 passed | coverage 93.3% of api/ | eslint 0 | tsc 0 | next build 0 | e2e 23/23 | actionlint 0
- New tests (tests/test_db_concurrency.py, 4): SQLite WAL + 15 s busy timeout on; 12 threads x 25 save/load/feedback/kotak
  calls with no error; two connections writing the same file at once (400/400 rows); a deleted dalang.db is detected
  and reconnected (the "attempt to write a readonly database" from overlapping e2e runs).
- Concurrency (`bash scripts/load_local.sh`, fake Meta API, MAX_ACTIVE_JOBS=6): 6 films started at the same moment,
  6/6 done, 0 errors, every MP4 served, the 7th request answered 429 with the kind "Sang dalang sedang sibuk" message,
  nothing left active, 0 tracebacks / "database is locked" / "readonly" lines in the server log. Wall time 478.9 s with
  the 2-worker pool (per film 136.8 to 477.9 s, i.e. queued in pairs; this sandbox, shared CPU).
- Accessibility (`bash scripts/a11y_local.sh`, axe-core 4.12.1, WCAG 2.0/2.1 A + AA): home, film, watch, gallery, kotak on
  phone and desktop, 10 page checks, 0 violations (critical 0, serious 0, moderate 0, minor 0). docs/ACCESSIBILITY.md.
- CI: .github/workflows/ci.yml validated with actionlint 1.7.7 (0 findings); new `e2e` job runs scripts/e2e_local.sh.
- Demo video re-rendered: 165.5 s (2:45), 1280x720 h264 + aac, 15 shots (adds share bar, X link card, sample gallery).

## 2026-11-01 14:25 WIB
ruff 0 | mypy clean (56 files) | pytest 380 passed | coverage 99% (last measured, not re-run) | eslint 0 | tsc 0 | next build 0 | e2e 26/26 | axe 14 page checks, 0 violations
- New this round: Penjaga Budaya, consistency score, models receipt, Story Starters, read-along, A5 storybook, /judge, /guru, eval harness (d885dbd..db369f3).
- Demo video re-rendered: 173.2 s (2:53), 1920x1080 h264 + aac, 13 shots; teaser_60s 60.0 s (1920x1080), teaser_vertical 40.0 s (1080x1920). Placeholder art (fake Meta API), stand-in child voice labelled.

## 2026-11-02 02:30-04:00 WIB
ruff 0 | mypy clean (63 files) | pytest 457 passed (9 min 42 s) | coverage 97% (97.1% of api/, 4653 statements, 137 missed, `make coverage` re-run) | eslint 0 | tsc 0 | next build 0 | e2e 26/26 + web (Playwright, 390 px phone) 25/25 | axe 20 page checks, 0 violations
- After this run one regression test was added for the poster bug below (`tests/test_poster_title.py`, fails before the fix, passes after).

### Manual product smoke (fake Meta API, Chromium driven like a user; script `work/r5fin/smoke.py`, 19/19)
| # | What a user does | Result | Notes |
|---|---|---|---|
| 1 | Home -> Bahasa Indonesia -> Story Starter "Timun Mas" -> Jadikan wayang | PASS | film done, plays; language id |
| 2 | Home -> Basa Jawa -> "Kancil dan Buaya" | PASS | film done, language jv |
| 3 | Home -> English -> "Keong Mas" | PASS | film done, language en ("The Golden Snail") |
| 4 | Gara-gara mode film pauses for the choice | PASS | puppet's question shown |
| 5 | Class screen: Open the vote, QR; 3 phones (390 px) open /vote/{id} and tap A, B, B | PASS | tally [1, 2] live on the class screen, QR is a PNG |
| 6 | Teacher closes the vote | PASS | film continues with B, then finishes |
| 7 | Remix -> Villain's view | PASS | new film "... · told by Buto Ijo", remix_of set, same puppet PNGs (SHA-1 identical) |
| 8 | Sticker pack zip | PASS | 3 WebP stickers 512x512 RGBA, 13 KB each (<100 KB), tray.png 96x96, 47 KB zip |
| 9 | loop.gif | PASS | 480x270, 30 frames, loops forever, 114 KB |
| 10 | Storybook PDF (A5) | PASS | 299 KB, 7 A5 pages (419x595 pt) for a 5-scene film |
| 11 | Gamelan WAV previews | PASS | happy/slendro and tense/pelog 4.0 s, 24 kHz, audible; unknown mood -> 400; film score slendro / pathet manyura |
| 12 | /kelir/{id}: drag a puppet with the mouse | PASS | x 0.21 -> 0.49 of the stage |
| 13-17 | /pentas, /judge, /guru, /watch/{id}, /kelir/{id} on a 390 px phone | PASS | HTTP 200, no horizontal overflow (390 px), no page errors |
| 18 | No uncaught page errors in the desktop flows | PASS | |

Bugs found and fixed:
- **Poster title ran into the tagline** for long titles (a remix "Timun Mas lan Buto Ijo · told by Buto Ijo" wrapped
  to a second 54 px line over "Dalang AI · a wayang film..."; it is the video's poster frame on /film and /watch).
  The title now shrinks to fit one line (54 -> 34 px) and only very long titles take two smaller lines inside the band
  (`api/pipeline/engine.py` `poster`; test `tests/test_poster_title.py`).

Seen, not a bug in the product: the fake Meta API answers with one of three fixed scripts chosen by story keywords,
so in fake mode a Timun Mas story told in Bahasa Indonesia gets the Javanese fixture's title ("Timun Mas lan Buto
Ijo"), a Kancil story in Basa Jawa gets the Indonesian narration, and the Malin Kundang starter gets the Kancil
gara-gara question. With the real key Muse Spark writes the script in the chosen language.

Demo re-rendered (v3): 174.3 s (2:54), 1920x1080 h264 + aac 48 kHz stereo, 13 shots (classroom vote, Kelir Live,
home hero, pipeline theatre, stickers new; storyboard and Kotak Wayang shots cut); the close card keeps its lines
above the caption area and holds 4.7 s after the last caption. teaser_60s 60.0 s (1920x1080) and teaser_vertical
42.0 s (1080x1920) open on Kelir Live. Over 40 stills from the three renders checked by eye (labels, placeholder marks, captions); the 9:16
phone recording was first padded with grey (fixed: cropped to the phone viewport).

## 2026-11-02 (redesign, voices, demo re-recorded)

The site moved to the night-show design system ([DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)) and the narrator defaults
changed ([VOICES.md](VOICES.md)). After that: e2e 26/26, the phone browser checks 25/25, the axe audit 0 violations
on 22 page checks (the 404 page is new), and every page re-shot on a phone and a desktop with
`web/e2e/ui_shots.py` (`docs/screenshots/ui/after/`, old design kept in `ui/before/`). The demo was re-recorded on
the new site with a Kokoro-82M voice-over: 177.9 s (2:58), 1920x1080, -16.6 LUFS; teaser_60s 60.0 s and
teaser_vertical 42.0 s. I checked the storyboard stills
(`docs/demo/storyboard.jpg`) by eye: every UI shot shows the new design, and the placeholder labels are visible.

## 2026-11-03 (hardening and cheap phones)

I went through the app again on a production build (14 routes at 360, 390 and 1440 px, a keyboard walk, offline,
slow 3G) and fixed what a family or a judge would hit: raw recordings could be fetched from `/media` by anyone with
the film id, a forged `X-Forwarded-For: 127.0.0.1` skipped the hourly limit, uploads were read whole before the size
check, there were no security headers, Sembah could be counted any number of times, the microphone stayed on after
leaving the page, offline pages showed the browser's error, the film page polled forever, and puppet rods ran through
the captions. After the fixes: pytest <!-- facts:tests -->520<!-- /facts --> tests (one SSE test timed out waiting
for its server under parallel workers and passes alone; its wait was raised in ad37e64), coverage
<!-- facts:coverage -->96%<!-- /facts -->, e2e 26/26, the phone browser checks 25/25, axe 0 violations on 22 page
checks, and 21/21 after-checks for the fixes themselves. Two findings are left as they are: the hourly limit still
trusts the first forwarded address (the films-in-progress cap and the spend caps still bound it), and the home page is
725 KB on first load.

Later the same day the re-shot screenshots caught a film whose "Painting the scenes" stage failed with a raw error
and a server path. Two films with the same story were writing and reading one cached picture at the same moment, and
one copied it half-written. Cached pictures are now written to a temp file and swapped in, one film at a time per
cached picture, and a damaged entry is repainted. A failed film now shows a kind bilingual message and never the raw
error text or a path. 21 new tests cover it; the whole suite is <!-- facts:tests -->520<!-- /facts --> tests, all
passing, coverage <!-- facts:coverage -->96%<!-- /facts -->, and every page was re-shot.

## 2026-11-04 (submission day)

I walked every page again on a production build with the fake Meta API, at 360 and 1440 px, once on a brand-new
server with nothing made yet (what a judge sees right after a deploy) and once with a finished film. No console errors
on any real page, and all 24 same-site links answer (the only 404s are the 404 pages). What I fixed: the judge page
showed developer text when there was no sample film, its API docs link went to a page the website doesn't serve, a
film page for a missing film kept polling, the home page gave up after one slow health check, a failed film lost the
typed story, and the gallery's empty state was Indonesian only. Details in the README's "Added Nov 4".

After the fixes:

| Check | Result |
|---|---|
| pytest (full suite, 2 workers) | <!-- facts:tests -->520<!-- /facts --> passed, 0 failed, <!-- facts:coverage -->96%<!-- /facts --> line coverage of `api/` (4,989 statements, 198 missed) |
| ruff, mypy (67 files) | 0, 0 |
| eslint, tsc, `next build` | 0, 0, OK |
| Full-stack e2e (`scripts/e2e_local.sh`) | <!-- facts:e2e -->27/27<!-- /facts --> steps (new step: the judge page's API docs link works through the website), web checks 25/25 |
| axe-core (`scripts/a11y_local.sh`) | <!-- facts:a11y -->22<!-- /facts --> page checks, 0 violations |
| Nov 4 fixes checked in a browser | 12/12 |
| `go_live.py --preflight --dry-run` | 6/6 models answer on the fake API, $0 |
| r5_perf (390 px phone, cold, median of 3) | all targets met; home LCP 680 ms, Pentas 692, most applauded 572, Kelir Live 740, Watch 948, CLS 0.000 everywhere |

The home LCP is higher than Nov 3's 452 ms with the same home bundle. This run shared the machine with the demo video
encode and other jobs, so I put the difference down to machine load. It's still under the 1.5 s target.

Two small things are left open: a self-hosted `next start` sends JavaScript uncompressed (compression stays off so
the live progress stream isn't buffered; Vercel compresses at its edge), and a failed voice recording still has to be
recorded again (a typed story is kept).
