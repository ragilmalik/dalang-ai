# Changelog

Dates are WIB (UTC+7). The project was built during the Meta Global AI Developer Hackathon, Oct 26 to Nov 4, 2026;
Nov 5 is the go-live on the real Meta Model API.

## 2026-11-07: final check

* Re-ran everything on a fresh machine: pytest, coverage, ruff, mypy, the local end-to-end runs, the browser runs,
  the accessibility checks, the voice and wording checks and the facts check.
* Fixed: the Kancil and Timun Mas sample films said their music was the code-made gamelan, but they play the Kraton
  recording. Their saved score now names and credits the recording, and a new test keeps all three samples honest.
* Fixed: `requirements-tts.txt` didn't list Pocket TTS, the demo narrator. It does now.
* Fixed: the credits table in the README still said all the gamelan was made in code. It now credits the Kraton
  recording (CC BY 4.0), Pocket TTS and the labelled AI-generated scenes in the demo. Same fix in README.id,
  WRITEUP and MALIK_CHECKLIST, and in a stale docstring in `api/pipeline/engine.py`.
* Rebuilt the demo storyboard from the new 178.2 s video.

## 2026-11-06 (afternoon): media remake (art, music, voice, video, screenshots)

* The art looks like real puppets now. The Muse Image prompts ask for a hand-carved buffalo-rawhide puppet with
  chiselled holes, real gold leaf and horn rods, photographed in sharp detail, and for backdrops photographed through
  a lamp-lit cotton screen that fills the frame (`api/prompts.py`). The quality checker accepts photo-like puppets
  and still rejects 3D, cartoons and real people.
* The three sample films were made again on the live Meta Model API with those prompts (`content/samples/`), and the
  home page loop and share poster come from the new Kancil film.
* Real gamelan: every film now plays a recording of the court musicians of the Kraton Ngayogyakarta (RTB45,
  CC BY 4.0, `assets/music/`) under its scenes, a calm excerpt for calm and night scenes and a lively one for the
  rest, ducked under the narration. `GAMELAN_SOURCE=procedural` brings back the gamelan made in code. The credit is
  in the site footer, the film end card of the demo and `assets/music/README.md`.
* New narrator engine: Pocket TTS (Kyutai, MIT). The demo voice-over is `pocket:caro_davy` (a CC0 LibriVox voice):
  UTMOS 4.43 against Kokoro's 4.54, but 9.8% word errors against 16.3%. Scores in `docs/VOICES.md`.
* The demo video was recorded again (2:58, -16.8 LUFS) with four AI-generated photo-style scenes of a child, a
  family, a classroom and a backyard shadow play. Each is labelled "AI-generated scene" while it is on screen, and
  the app screens inside them are real screenshots (`docs/demo/broll/README.md`). New thumbnail, teasers and launch
  clips from the same run.
* Every page re-shot on the live app, phone and desktop (`docs/screenshots/ui/after`, README crops).

## 2026-11-06: polish pass (layout shift, page weight, tap targets, day mode, wording)

* Pages no longer jump while they fill in. The footer used to slide down once a film page loaded (layout shift
  0.78 on desktop); the main area now reserves a screen of height and the scrollbar keeps its gutter. The home
  page film no longer moves when the font loads. Every page measures under 0.1.
* Gallery and Pentas load about half the bytes (1.2 MB down to about 0.5 MB): the cards use an 800 px WebP made
  once per film (`api/thumbs.py`), and the full poster stays as the big `srcset` choice.
* Every small button and link a thumb needs is at least 44 px tall: small buttons, footer links, the logo, the judge
  page links and "Every step".
* Puppet pictures have a width and height, so nothing reflows when they arrive.
* Day mode turns the phone's browser bar light too.
* The accessibility audit now checks day mode on a phone as well (33 page checks, up from 22). `scripts/facts.py`
  counts those rows and also reads the browser check count from the e2e log.
* I went through the wording of every doc, comment and docstring. `scripts/voice_check.py` flags AI-sounding words
  (the list comes from Wikipedia's "Signs of AI writing" page and a few word studies), notes that read like
  instructions to a coding tool, and dashes. The eval report, the dated test and verification reports, the
  deploy checklist and the demo footage notes got the most rewrites; facts and numbers stayed the same.
  `tests/test_voice_check.py` fails if any of it comes back.
* The recorder's double-tap check in the browser tests taps inside the page, in the first frame the ring shows.

## 2026-11-06: smoother site (motion and recorder pass)

* Page transitions: the old page dims out, the new one rises in; the header stays put (`app/template.tsx`).
* A gallery or Pentas poster morphs into the film player on the watch page.
* Gallery and Pentas show a card-shaped loading state right away instead of a blank wait.
* Recorder: start and stop notes plus a short buzz, a ring that fills over the 90 seconds, an early double-tap on
  Stop is ignored, and screen readers hear when recording starts and ends. A tap during the microphone prompt no
  longer starts a second recording.
* Progress and vote bars animate with `transform` instead of `width`, so they stay smooth on slow phones.
* Every new motion turns off with `prefers-reduced-motion`.

## 2026-11-06: media on the live API, final checks

Recorded on the live Meta Model API
* Demo video (2:57), both teasers, the three X launch clips, the YouTube thumbnail and all 28 page screenshots, the
  README crops, the agent trace, Kotak Wayang and the printable puppet. Nothing judge-facing comes from the fake API
  any more.
* The demo's close card names the public repo; it no longer shows a placeholder line for an undeployed app.
* The demo's app shots sit on a quiet procedural gamelan bed instead of silence (`GAMELAN_BED_VOLUME`).
* The "why" line in the demo no longer makes a claim about kids in Semarang that I haven't measured.

Fixed
* Muse Wonder motion plans with an out-of-range number (a keyframe angle past 25 degrees, seen live) were thrown away
  for a rule-based glide. They're clamped and kept now, and the trace says how many values were clamped.
* `make_launch_clips.py` judges a film passed on the command line by that film (or `FAKE_META`), not by the old
  `data/demo/job.json`, so live clips don't get a "placeholder art" label.
* From the final checks: `next start` gzips JS while the progress stream stays unbuffered; a recording for a film
  that failed stays on the device so it can be sent again; the judge page wording; tutorial and doc fixes.

## 2026-11-05: live on the Meta Model API

First runs against the real API (api.meta.ai) with a real key. Results per model: [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md).

Fixed after real calls
* The preflight and the request recorder built their own HTTP transport, which ignored `HTTPS_PROXY` and
  `SSL_CERT_FILE`, so behind a proxy every call got 401. `meta_client.real_transport()` now reads both.
* SAM 3.1: the bare word "puppet" found no mask on real Muse Image puppet sheets, while the creature's noun did. The
  cut-out now tries the script's phrase, then the phrase without "puppet", then "puppet".
* Muse Spark 1.3 can spend its whole output budget on reasoning and return no content. Structured-output calls now
  retry once with `reasoning_effort: low` and fail with a clear error if the answer is still empty.
* ffmpeg's MP4 trailer write failed with an I/O error on a network filesystem. `ENCODE_DIR` encodes on a local disk
  and moves the finished file.

Real content instead of placeholders
* The three sample films (Kancil, Timun Mas, The Golden Snail) were made with the live models and ship in
  `content/samples/`. They load into the gallery on first start and are labelled as sample stories written for this
  project. Sample films' title cards say "contoh cerita / a sample story" instead of "a story told by a child".
* The website's hero loop, poster, share images and README pictures come from those films.
* The sample recording is now `assets/sample-story/sample_story_synthetic.mp3`: a synthetic voice at normal pitch,
  labelled as synthetic. It is not a child and not a real person.
* Removed: the testimonials feature and its ten invented quotes, the sample rows in the family-testing log, and the
  QR code that pointed at a made-up address. QR codes now use the visitor's own address until `PUBLIC_BASE_URL` is
  set.

Running it
* Three modes, reported by `GET /api/health`: `live`, `fake` (`FAKE_META=1`, tests and offline) and
  `not_configured`. A server without a key no longer fakes films silently; it plays the samples and answers new film
  requests with a plain 503.
* `GET /api/ready` for load balancers: database, storage, ffmpeg and, when live, Meta API reachability.
* Structured logs (`api/logs.py`): request id (`X-Request-ID`), film id and stage timings on every line,
  `LOG_FORMAT=json`, credentials scrubbed. Unhandled errors return a kind message with the request id.
* New docs: [ARCHITECTURE.md](docs/ARCHITECTURE.md), [SETUP.md](docs/SETUP.md), this changelog.

## 2026-11-04: submission day

Judge page (`/judge`) shows whether the server runs live or on the fake API; the gallery empty state is bilingual; a
failed film keeps the typed story for a retry; the home page retries a slow `/api/health`. 520 tests, 96% line
coverage, e2e 27/27, axe 0 violations. Demo video re-recorded (made on the fake API).

## 2026-11-03: cheap phones and weak signal

Smaller pages and pictures, an offline-capable PWA shell, Kelir Live performance on low-end phones, a 6-films-at-once
load test.

## 2026-11-02: new look and new voices

Redesign (night-indigo kelir, Fraunces and Plus Jakarta Sans), a narrator listening test (docs/VOICES.md) and new
default voices.

## 2026-11-01: features

Gara-gara (the child chooses what happens next), classroom vote, Kelir Live (perform the puppets by hand), Kotak Wayang
(keep a puppet for the next story), printable puppets, Remix, Dalang Director, Penjaga Budaya cultural review,
models receipt and agent trace.

## 2026-10-29 to 10-31: the pipeline

FastAPI pipeline across the Meta models (listen, lakon, casting, SAM cut-outs, scenes, verify loop, motion, narration,
final cut), the Next.js app, the fake Meta API for tests, CI and deploy files.
