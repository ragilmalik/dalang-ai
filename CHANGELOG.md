# Changelog

Dates are WIB (UTC+7). The project was built during the Meta Global AI Developer Hackathon, Oct 26 to Nov 4, 2026;
Nov 5 is the go-live on the real Meta Model API.

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
