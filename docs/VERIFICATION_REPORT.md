# Verification report: Meta Model API usage

## Live run on the real Meta Model API (Nov 5, 2026)

On Nov 5 I ran Dalang AI against `https://api.meta.ai/v1` with my own key for the first time. The key was only in
the process environment; it is not in this repo, in any log or in any film. Costs below are the app's own meter,
which uses Meta's list prices, so they are estimates rather than an invoice.

### Preflight (`python scripts/go_live.py --preflight`, 22:45 WIB)

6/6 PASS, about $0.015 in total.

| Model | Latency |
|---|---|
| muse-voice-transcribe-1.0 | 0.9 s |
| muse-spark-1.3 | 2.7 s |
| muse-spark-1.2 | 2.8 s |
| muse-wonder-1.0 | 1.3 s |
| muse-image-1.0 | 15.9 s |
| sam-3.1 | 1.3 s |

The first attempt was 0/6 with HTTP 401. The preflight's contract guard built its own `httpx.HTTPTransport()`, which
ignores `HTTPS_PROXY` and `SSL_CERT_FILE`, so on my dev box, which goes out through a proxy, the request never reached Meta with the right
setup. `meta_client.real_transport()` fixed it; the recorder uses it too.

### One check per model and feature (23:10 WIB)

| Model | What I checked | Result | Latency | Est. cost |
|---|---|---|---|---|
| muse-voice-transcribe-1.0 | transcribe the synthetic sample story (30.9 s, Indonesian, `ENDPOINTING`) | PASS, 352 characters, 2 speech turns | 7.6 s | $0.0015 |
| muse-spark-1.2 | Javanese audio understanding (`input_audio` wav, synthetic jv-ID-SitiNeural clip) | PASS, understood, spelled phonetically | 2.9 s | $0.0026 |
| muse-spark-1.3 | structured output (`json_schema`), `reasoning_effort: low` | PASS, valid JSON | 4.9 s | $0.0021 |
| muse-wonder-1.0 | structured output (`json_schema`) | PASS, valid JSON | 5.1 s | $0.0083 |
| muse-image-1.0 | `images/generations` 1024x1024, `reasoning_strength: low` | PASS, 3.8 MB PNG | 20.5 s | $0.0100 |
| muse-image-1.0 | `images/edits` with 1 reference image | PASS, 3.9 MB PNG | 11.6 s | $0.0100 |
| sam-3.1 | `responses` stream, concept "puppet" on a generated puppet | call PASS, 0 masks (see below) | 3.0 s | $0.0025 |

About $0.037 in total.

### Three sample films made end to end

These are the films in `content/samples/`. The stories were written by me for this project; the films are labelled
"contoh cerita / a sample story". Every call below went to the live API, none failed and none needed a retry.

| Film | Language | Meta calls | Muse Spark 1.3 | Muse Image | SAM 3.1 | Muse Wonder | Est. cost | Consistency |
|---|---|---|---|---|---|---|---|---|
| Kancil yang Cerdik dan Buaya Sungai | Bahasa Indonesia | 24 | 12 calls, 89 s | 2 calls, 39 s | 5 calls, 16 s | 5 calls, 59 s | $0.26 | 98/100 |
| Timun Mas lan Buto Ijo | Basa Jawa | 36 | 12 calls, 107 s | 9 calls, 281 s | 10 calls, 27 s | 5 calls, 55 s | $0.36 | 99/100 |
| The Golden Snail Princess | English | 31 | 11 calls, 133 s | 7 calls, 180 s | 8 calls, 22 s | 5 calls, 50 s | $0.32 | 100/100 |

Kancil has only 2 Muse Image calls because a first attempt at that film failed in the final cut (an ffmpeg I/O
error, below) after its pictures were drawn; the second run reused them from the image cache. That first attempt
cost about $0.34 and is counted in the total. Latencies are the sum over calls for that model; calls inside a stage
run in parallel, so a film takes less wall time than the sum (about 5 to 8 minutes per film here, mostly Muse Image
and the render).

Everything I spent on the live API on Nov 5, preflight, checks and films together: about $1.40 by the app's meter.

### What the real calls showed, and what I changed

* **SAM 3.1** found no mask for the bare word "puppet" on real Muse Image puppet sheets, and sometimes none for the
  script's phrase either. Plain nouns worked: "deer" (confidence 0.67 to 0.78), "person" for the princess, "animal"
  and "creature". `segment.queries()` now tries the phrase, the phrase without "puppet", its head noun, a plain noun
  for the character's kind, then "puppet". The gunungan gets no mask for any phrase I tried; the plain-background
  cut-out handles it and the consistency score marks it as a fallback. The Golden Snail princess was first cut out by
  that fallback, which left a faint box around her in the film; I re-cut her with SAM ("person") and re-rendered the
  film without new model calls apart from that one SAM call.
* **Muse Spark 1.3** with a small `max_tokens` (200) spent it all on reasoning and returned no content. The app's
  structured-output calls send no `max_tokens`, and now retry once with `reasoning_effort: low` if a reply is empty.
* **Muse Spark 1.2** understands Javanese speech but writes it phonetically ("Biyan ono bucah waton" for "Biyen ana
  bocah wadon"). The script step works from the meaning, so the films are fine, but a Javanese transcript shown to
  a family would need that caveat.
* **Rendering**: ffmpeg's MP4 trailer write failed with an Input/output error on my dev box's network filesystem.
  `ENCODE_DIR` encodes on a local disk and moves the finished file.

## Media re-recorded on the live API (Nov 6, 2026)

The app ran live on my machine (`work/live/RUN_LIVE.sh`: key from the environment only, `MAX_USD_TOTAL=14`) and
everything judges see was recorded from it, 01:00-03:00 WIB:

| What | Result |
|---|---|
| Demo video `docs/demo/dalang-ai-demo.mp4` | 176.6 s (2:57), 1920x1080 H.264 + AAC, -16.7 LUFS, 13 shots, no silent gap longer than 1.5 s. Recorded from a real browser session of the live app; the film in it (`oHb6vrNE`, Kancil, Bahasa Indonesia, gara-gara on) was made by the live models while the camera ran |
| Teasers | `teaser_60s.mp4` 60.0 s 1920x1080, `teaser_vertical.mp4` 42.0 s 1080x1920 |
| X launch clips | `docs/launch/clip1-3`, 22.0, 20.0 and 18.0 s, from the same live film, no placeholder label |
| Thumbnail | `docs/demo/thumbnail.jpg`, 1280x720, a scene still from the live film |
| Screenshots | 28 full pages (`docs/screenshots/ui/after/`, 390 px phone and 1440 px desktop), the README crops, the agent trace, Kotak Wayang and the printable puppet, all from live films (`oHb6vrNE` done, `zrKl8cwB` at the gara-gara question, `yIJIENvN` at the storyboard, `ffTGxca3` caught while being made) |
| Spend | $1.387 before, $2.527 after: about $1.14 for four live films (one of them stopped at the storyboard and one at the gara-gara question) |

What the narrator is: a synthetic voice (Kokoro-82M `af_heart`), labelled as a stand-in in the docs. The child's
voice in the first 3 s is a labelled synthetic stand-in. The three classroom "phones" in the vote shot are API calls
from the recording script.

What I checked by eye: every 5 s of the demo as a contact sheet, every 4 s of both teasers and all three clips, and
all 28 screenshots. Two things I fixed on the way:
- The close card still said "Live app link: added after deploy (PLACEHOLDER)" and "github.com/ragilmalik/dalang-ai
  (planned)". It now names the public repo, and shows a live-app line only once one exists (new test).
- The Kelir Live and close shots had up to 9 s of total silence where the voice-over pauses. The app shots now sit on
  a quiet bed from the app's own procedural gamelan (`GAMELAN_BED_VOLUME`, default 0.28; new test).

A real bug the live trace showed: in film `oHb6vrNE`, Muse Wonder's plan for scene 5 had one keyframe angle just past
the 25 degree limit, and the strict schema threw the whole plan away for a rule-based glide. `animate.clamp_motion`
now pulls out-of-range numbers to the nearest allowed value, keeps the model's plan and records how many values it
clamped in the trace (two new tests). The screenshot of that film's trace still shows the old fallback line, because
that's what happened when it was made.

## Request shapes checked against Meta's docs (Oct 30, 2026)

Every endpoint, model id and request field used by `api/meta_client.py` was checked against Meta's
public developer docs on **2026-10-30 (02:30-03:00 WIB)**. Sources are the docs pages below.

| Use | Model id | Endpoint and fields we send | Source |
|---|---|---|---|
| Transcribe story | `muse-voice-transcribe-1.0` | `POST /v1/asr/transcribe?sessionId=…` multipart: `request` JSON (`mode: ENDPOINTING`, `model`, `audioEncoding: WAV`, `languageBias`, `keywords`) + `audio` (mono 16-bit PCM WAV, 16 kHz, ≤10 min, ≤32 MB). Reads `transcript`. | https://dev.meta.ai/docs/speech-to-text |
| Javanese audio | `muse-spark-1.2` | `POST /v1/chat/completions`, content part `{"type":"input_audio","input_audio":{"data":<base64 wav>,"format":"wav"}}`, `max_tokens: 4000`. Docs recommend 1.2 for audio. | https://dev.meta.ai/docs/video-understanding |
| Script, safety, verify | `muse-spark-1.3` | `POST /v1/chat/completions` with `reasoning_effort` and `response_format: {"type":"json_schema","json_schema":{"name","schema"}}`; images as `{"type":"image_url","image_url":{"url": data URL}}` | https://dev.meta.ai/docs/structured-output , https://dev.meta.ai/docs/image-understanding |
| Motion planning | `muse-wonder-1.0` | same Chat Completions call with an image part and a JSON schema. Muse Wonder outputs text only. | https://dev.meta.ai/docs/models |
| Puppets, backdrops | `muse-image-1.0` | `POST /v1/images/generations` `{model, prompt, n, size "WxH", output_format: png, reasoning_strength, tool_enablement{enable_web_search, enable_shell, enable_image_search}}`; reads `data[0].b64_json`. Unknown top-level fields return 400, so none are sent. | https://dev.meta.ai/docs/image-generation |
| Cut-outs | `sam-3.1` | `POST /v1/responses` `stream: true`, input message with `input_text` (noun phrase) + `input_image` (data URL), `metadata: {"mask_encoding":"one_bit","include_confidence":"true"}`; parsed with Meta's `meta-sam-parser` 0.1.0 (`parse_responses_stream`, `image_segmentation_format`, `decode_mask_to_raster`). Masks are box-local. | https://dev.meta.ai/docs/media-segmentation , https://dev.meta.ai/docs/sam/client-libraries |
| Open weights | Muse Spark Open | Baseten `https://inference.baseten.co/v1/chat/completions`, model `meta-models/muse-spark-open` (configurable `OPEN_MODEL`) | https://dev.meta.ai/docs/muse-spark-open/deploy |

Base URL `https://api.meta.ai/v1`, header `Authorization: Bearer <key>`. Prices used by the cost
meter (https://dev.meta.ai/docs/pricing-rate-limits): Muse Spark $1.25 in / $4.25 out per 1M tokens,
Muse Wonder $4 / $20, Muse Image $0.01 per image, SAM 3.1 $2.50 per 1,000 images, Voice Transcribe $0.18 per hour.

## Differences from SPEC.md, and what we did

| SPEC.md says | Docs say | Implementation |
|---|---|---|
| Muse Wonder animates each scene into a 4-8 s clip | Muse Wonder is a text-output model; no Meta video model exists | Muse Wonder returns a keyframe MotionPlan per scene (validated by Pydantic); `api/pipeline/engine.py` renders it |
| Use a Meta TTS model if available | None documented; Voice Transcribe is speech-to-text only | `edge-tts` neural voices, documented in README |
| Muse Voice Transcribe for all three languages | Javanese is not among its 25 languages | Javanese audio goes to Muse Spark 1.2 audio understanding |
| Baseten id `meta-models/muse-spark-open-1026` | Docs list `meta-models/muse-spark-open` | Default is the documented id; `OPEN_MODEL` env overrides |

## How the request shapes are kept honest

* `tests/test_meta_client.py::test_request_shapes_match_docs` captures the exact HTTP requests and checks URL, model, fields and auth header.
* `api/fake_meta.py` mirrors documented validation (e.g. rejects unknown Muse Image fields with 400, requires both multipart parts for ASR, accepts only `sam-3.1` streaming), so a malformed request fails in tests too.
* `scripts/check_keys.py` makes one real call per model (about $0.03 in total) once a key exists.

## Not yet verified against the live API (needs my key)

Live responses for each model. Run `python scripts/check_keys.py`; the result should be added here.

## Re-verification, 2026-10-30 05:05 WIB (Oct 29, 22:05 UTC)

Fetched the docs again (markdown versions, `https://dev.meta.ai/docs/<page>.md`) and compared them with `api/meta_client.py` and `api/config.py`:

| Check | Doc page | Finding |
|---|---|---|
| Model lines and ids | https://dev.meta.ai/docs/models | Hosted: Muse Wonder (`muse-wonder-1.0`), Muse Spark (`muse-spark-1.3` recommended, `muse-spark-1.2`, `muse-spark-1.1`), Muse Image (`muse-image-1.0`), Muse Voice Transcribe (`muse-voice-transcribe-1.0`), SAM (`sam-3.1`). Open weights: Muse Spark Open, Muse Glimmer. Matches config. |
| No video model | https://dev.meta.ai/docs/models | Output columns are Text, Image, Text (transcription), Text (geometry). No video output. Unchanged. |
| No TTS | https://dev.meta.ai/docs/models | Muse Voice Transcribe "returns transcript text. It does not synthesize speech or provide a speech-to-speech conversation API." Unchanged. |
| Audio on Spark | https://dev.meta.ai/docs/models , https://dev.meta.ai/docs/video-understanding | "Audio understanding in Muse Spark 1.3 is not fully supported… use Muse Spark 1.2"; `input_audio` content part on Chat Completions. Matches. |
| Voice Transcribe languages | https://dev.meta.ai/docs/speech-to-text | 25 languages incl. Indonesian, Malay, English; Javanese not listed. `POST https://api.meta.ai/v1/asr/transcribe?sessionId=…` multipart. Matches. |
| Muse Image fields | https://dev.meta.ai/docs/image-generation | `POST /v1/images/generations`; `output_format` (webp default, png, jpeg); `reasoning_strength` high/low; `tool_enablement.{enable_image_search, enable_web_search, enable_shell}`. Matches. |
| Structured output | https://dev.meta.ai/docs/structured-output | `response_format: {type: "json_schema", json_schema: {…}}`. Matches. (We do not rely on the model always returning valid JSON: Pydantic validation + one retry.) |
| SAM 3.1 | https://dev.meta.ai/docs/media-segmentation , https://dev.meta.ai/docs/sam/client-libraries , https://dev.meta.ai/docs/sam/reading-segmentation | Responses API streaming; `metadata.mask_encoding: "one_bit"`; `include_confidence: "true"` needs `meta-sam-parser` ≥ 0.0.6 (we pin ≥ 0.1.0). Matches. |
| Muse Spark Open on Baseten | https://dev.meta.ai/docs/muse-spark-open/deploy | Hosted-providers table: Baseten model `meta-models/muse-spark-open` (same string for Together AI, Groq, Nebius). Our default matches; `-1026` still not in the docs. |
| Prices | https://dev.meta.ai/docs/pricing-rate-limits | Muse Image $0.01/image; SAM billed per image; Spark $1.25/$4.25, Wonder $4/$20 per 1M tokens. Matches `api/cost.py`. |

Result: no changes needed to endpoints, model ids or fields.

## Build and demo verification, 2026-10-30 19:30 WIB (12:30 UTC)

Real results from this dev box (2 vCPU, linux-arm64), fake Meta API (`FAKE_META=1`, no key):

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `mypy api scripts` | Success, 34 source files |
| `pytest -q` | **52 passed** in 97.8 s (after the rotation-cache test; 51 before) |
| `web: npm run lint` / `typecheck` / `build` | 0 problems / clean / compiled, routes `/`, `/film/[id]`, `/gallery`, `/watch/[id]` |
| Browser for recorders | `python -m playwright install chromium` fails here (CDN returns 403 for linux-arm64). Recorders no longer hardcode a path: `scripts/browser_path.py` tries `$CHROME`, Playwright's download, then system Chrome/Chromium (found `/usr/bin/chromium` 156). Playwright's own ffmpeg (needed for video capture) installed with `playwright install ffmpeg`; the demo script now does that by itself, and with no browser at all it falls back to the HTTP API + screenshots + ffmpeg. |
| Demo video | `docs/demo/dalang-ai-demo.mp4`: **129.8 s**, 1280x720 H.264 + AAC, 8.4 MB, English voice-over (edge-tts), burned-in captions (top-aligned while the film's own subtitles show), plus `.srt`, `voiceover.txt`, `timeline.json` (`browser_recording: true`, `recorded_in_fake_mode: true`), `thumbnail.jpg`. Recorded from a real Chromium session of the running app. Audio mean -23 dB, peak -6 dB. |
| End-to-end demo flow | type story → 7 stages → storyboard review → approve → film → share → watch page Sembah → gallery: all passed in the recording. Stage times: listen 1.2 s, lakon 1.2 s, casting 15.0 s, scenes 7.7 s, animate 18.2 s, narrate 8.7 s, cut 273 s (with another project's renders on the same 2 cores). |
| Final-cut speed | 16:9 + 9:16 now render in parallel threads (`RENDER_WORKERS`, default 2), and rotated puppets come from a small cache (0.2° steps; frame difference vs. before: mean < 0.1/255). Same 65 s film, 24 fps, both formats: 148.2 s (1 worker, no cache) → 112.2 s (2 workers) → **60.1 s** (2 workers + cache; 76.4 s with 1 worker). The dev box is shared with other projects' renders, so treat these as rough. Per-frame render alone: 14.1 → 10.6 ms. |
| Screenshots | `docs/screenshots/1-6` re-captured (new: `5-watch.png` with Sembah and "Behind the puppets", `6-gallery.png`). Fixed a repeated background band on tall pages (`globals.css`). |

Still not verified: live Meta responses (needs `META_API_KEY`; run `python scripts/check_keys.py`), phone mic over https, Docker image (no docker here; CI job builds it).

### Next up
1. Meta key → `check_keys.py` → re-render `make_demo_video.py` so the video shows real Muse Image art (one command).
2. Public repo + video upload + Cerebral Valley form + X post (all mine to do; see `docs/SUBMISSION_CHECKLIST.md`).
3. Optional polish: a vertical (9:16) cut of the demo video for the X post, made from `docs/demo/` segments; real-art screenshots after the key works.

## Re-verification 2026-10-31 09:15 WIB (ten upgrades)
- allchecks on c71e40c: ruff exit 0; mypy no issues (45 source files); pytest 100 passed; eslint 0 problems; tsc exit 0; next build exit 0 (/kotak route).
- Web e2e (scripts/e2e_local.sh, fake Meta API): 21/21 passed, incl. Kotak Wayang save + reuse, Gara-gara pause/choice (69.8 s film).
- go_live.py --dry-run: 8/8 steps passed (fake API).
- Demo video 133.1 s (2:13), 1280x720 h264+aac, 12 shots. Submission kit rebuilt: 57 files, zip 51.0 MB.
- Still MOCK/placeholder: all art (fake Meta API), sample recording, QR link (dalang-ai.example), 10 testimonials (placeholder: true), family-testing log rows, cultural-review sign-off.

## Re-verification 2026-10-31 11:50 WIB (polish pass)
- ruff/mypy clean (45 files); pytest 112 passed; eslint/tsc/next build exit 0; e2e 22/22 (new agent-trace step).
- Path traversal on /media fixed + regression test; bandit -ll clean; npm audit --omit=dev and pip-audit 0 vulnerabilities.
- Clean clone via README start.sh works; no overflow at 390 px.
- Demo video 143.4 s (2:23); submission kit zip 53.4 MB. Art, sample recording, QR link, testimonials remain labelled placeholders.

## Re-verification 2026-10-31 14:40 WIB (polish pass 2)
- ruff 0; mypy clean (51 files); pytest 132 passed; coverage 93% of api/; eslint/tsc/next build exit 0; bandit -ll 0; e2e 23/23.
- New: X/Open Graph link previews, ShareBar, PWA manifest, 3 labelled sample films (id/jv/en), restart recovery + cleanup, OpenAPI docs, Makefile, open-weights fake-mode tests, compressed images.
- Demo video 2:23 (143.4 s); submission kit zip 42.7 MB. Placeholders still labelled.

## Re-verification 2026-11-01 05:00 WIB (polish pass 3)
- ruff 0; mypy clean (53 files); pytest 136 passed; coverage 93.3% of api/; eslint/tsc/next build exit 0; e2e 23/23; actionlint 0.
- axe-core accessibility audit: 10 page checks (5 pages x phone/desktop), 0 violations. Load test: 6 simultaneous films, 6/6 done, 0 errors, 7th gets 429.
- SQLite now WAL + busy timeout + reconnect if the file is replaced. New: README.id.md, CONTRIBUTING, CODE_OF_CONDUCT, issue templates, CI e2e job.
- Demo video 2:45 (165.5 s, ffprobe), 15 shots incl. share bar, X link-card preview (labelled illustration) and the labelled sample gallery.
- Still placeholder/MOCK and labelled: all art (fake Meta API), sample recording, QR link (dalang-ai.example), 10 testimonials. Open weights wired and tested on the fake API only.

## Re-verification 2026-11-01 05:20 WIB (scheduled re-run)
- Added `tests/test_text_style.py` (no em dashes in any tracked text file) and cleaned the last four in `docs/SPEC.md`.
- ruff 0; mypy clean (53 files); pytest 137 passed (578 s on my shared dev box); eslint 0; tsc 0; next build exit 0.
- Nothing else changed since bb7c074. Still placeholder/MOCK and labelled: art, sample recording, QR link, testimonials; live Meta keys not yet verified.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 06:10 WIB (scheduled re-run, recording sweep)
- New: `runner.sweep_recordings` deletes any story.wav / upload.* older than `RECORDING_TTL_HOURS` (default 6) on start and on each new film, and strips the stored words of the speech turns; films still being worked on are skipped. Closes the "unapproved storyboard keeps the child's recording" known limit. 2 new tests.
- ruff 0; mypy clean (53 files); pytest 139 passed (470 s on my shared dev box); eslint 0; tsc 0; next build exit 0.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 06:30 WIB (scheduled re-run, doc links)
- New `tests/test_doc_links.py`: every relative link in the tracked Markdown files must resolve to a file (all do today). facts.json test count 140.
- ruff 0; mypy clean (53 files); pytest 140 passed (402 s). Web untouched since the last green build.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 07:00 WIB (scheduled re-run, API validation)
- New `tests/test_api_validation.py` (14 cases): bad language / empty story / bad narration voice create nothing; malformed or unknown film ids are 404 on every film route; approve, choice, scene edit and share in the wrong state are 409 and change nothing; applause counts only for public finished films; feedback ratings and pages are checked; Kotak family ids and files; QR only points at our own site; /api/health leaks no secrets.
- ruff 0; mypy clean (53 files); pytest 154 passed (635 s on my shared dev box); eslint 0; tsc 0; next build exit 0. facts.json test count 154.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 07:20 WIB (scheduled re-run, cost meter and storage)
- New `tests/test_cost_storage.py` (12 cases): token pricing, unknown model ignored, budget check boundary, trace cap, labels restore after errors, per-model summary, R2 upload (stubbed boto3) and local fallback. facts.json test count 166.
- ruff 0; mypy clean (53 files); pytest 166 passed (470 s). Web untouched since the last green build.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 07:50 WIB (scheduled re-run, runner failure paths)
- New `tests/test_runner_failures.py` (10 cases): a crashing stage fails the film and marks the running stage; long errors are trimmed; a blocked story is "blocked", not "failed"; the child's recording and its words are deleted on failure; cost is saved even when a stage fails; DEMO_MODE replays the prepared film (and does not when off or when no film exists); the cost meter is cleared after every run. facts.json test count 176.
- ruff 0; mypy clean (53 files); pytest 176 passed (353 s); eslint 0; tsc 0; next build exit 0.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).

## Re-verification 2026-11-01 08:30 WIB (scheduled re-run, listen and puppet cut-out)
- New `tests/test_listen_edge.py` (10 cases): nothing to hear or type is a kind block; typed stories skip transcription; unreadable recordings are blocked and deleted; too-short stories ask again in id/jv/en; the child's voice is kept only when speech timestamps exist; recordings are trimmed to the maximum length.
- New `tests/test_puppet_segment.py` (9 cases): SAM masks become trimmed transparent cut-outs; empty or degenerate masks give none; touching confident parts are kept, far or unsure ones dropped; background-key fallback; SAM retry with "puppet", SAM errors fall back, a budget stop is not swallowed. Raises the weakest-covered modules (puppet 69%, segment 77%). facts.json test count 195.
- ruff 0; mypy clean (53 files); pytest 195 passed (341 s). Web untouched since the last green build.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: tests for `media.py` narration fallbacks (67% covered) and `meta_client` error branches (83%).

## Re-verification 2026-11-01 09:00 WIB (scheduled re-run, narration fallbacks and Meta client errors)
- New `tests/test_media_meta_errors.py` (44 cases): WAV round trip, clipping and trimming; ffmpeg failure message; narration picks the language voice, slows down 8%, retries in a subprocess without proxy settings, and returns None (subtitles only) when the voice is unreachable or undecodable. Meta client: 429/5xx backoff 2s, 4s; 4xx never retried; timeouts; failed calls recorded in the agent trace; fenced or chatty JSON; open-weights and Glimmer fall back to `json_object`; open-weights calls are not billed to the Meta meter; malformed ASR turns skipped; Javanese audio part shape; edit_image caps references at 10; SAM errors and retries.
- ruff 0; mypy clean (53 files); pytest 239 passed (506 s); line coverage of api/ 96.4% (media.py 96%, meta_client.py 98%). facts.json: 239 tests, coverage 96. Web untouched since the last green build.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: check the least-covered api modules from `make coverage` and add tests; re-run web lint/typecheck/build if web/ changes.

## Re-verification 2026-11-01 09:45 WIB (scheduled re-run, animate, narrate, jobs, SSE, puppet box)
- New `tests/test_animate_narrate.py` (29 cases): rule-based motion for jump, bow, fly and plain sway; first-scene entrances; tense-scene tremble; Muse Wonder plan kept, unknown puppets dropped, missing puppets given a glide-in, bad or failing model falls back; partial re-render reuses saved plans and re-encodes a missing clip; child-voice grouping, plan, ffmpeg cut and TTS fallback; narrate detail lines for TTS, subtitles only, child voice and mixed.
- New `tests/test_jobs_qr.py` (8 cases): job cache and DB reload, `wait_change` timeout and wake-up from another thread, QR PNG and save.
- New `tests/test_api_kotak_sse.py` (13 cases): puppet box 404, idempotent save, full box 409; SSE stream ends for a finished film, follows a running one, 404 for unknown; loopback detection.
- ruff 0; mypy clean (53 files); pytest 289 passed (324 s); line coverage of api/ 97.9%. facts.json: 289 tests, coverage 98. Web untouched since the last green build.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: remaining gaps are fake_meta branches, garagara edge branches and main.py error paths; re-run web lint/typecheck/build if web/ changes.

## Re-verification 2026-11-01 10:00 WIB (scheduled re-run, fake Meta API, gara-gara units, API corners)
- New `tests/test_fake_meta.py` (29 cases): the keyless demo's stand-in for Meta is itself tested. Bearer auth, unknown routes, moderation, lakon fixtures by story and language, Javanese audio, polish, motion plans, gara-gara question and rewrite, ad-hoc schemas, Glimmer and Baseten model strings, image validation and sizes, the scripted redraw loop, SAM box and mask grammar, ASR multipart and turns.
- New `tests/test_garagara_units.py` (21 cases): who asks the question, how a spoken or typed answer is heard and deleted, rewrite validation and the single retry, Glimmer polish and its failure fallback, sample seeding thread.
- New `tests/test_main_gaps.py` (8 cases): unknown style falls back to classic, shutdown warning, oversized or empty gara-gara answers, SSE keep-alive ping and disconnect handling.
- ruff 0; mypy clean (53 files); pytest 347 passed (415 s); line coverage of api/ 99% (fake_meta.py and main.py 100%); eslint 0; tsc 0; next build exit 0. facts.json: 347 tests, coverage 99.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: api/ coverage is near complete; spend time on making the web e2e run less flaky (re-run `scripts/e2e_local.sh` when no other run is active), demo polish, and docs proofreading.

## Re-verification 2026-11-01 10:50 WIB (scheduled re-run, full browser pass)
- Installed Chromium again (`apt-get update` first; my dev box had lost it) and ran the browser-level checks on the current build, one at a time to avoid port and SQLite collisions.
- `scripts/e2e_local.sh`: 23/23 passed (film in 64.8 s, Gara-gara film in 69.8 s, share, QR, PDF, Kotak Wayang, trace).
- `scripts/a11y_local.sh`: axe 10 page checks, 0 violations, 0 serious or critical.
- `scripts/load_local.sh`: 6 simultaneous films all finished (wall 560 s on my shared 2 vCPU dev box), the 7th request got a kind 429, no server log errors.
- Fix: `scripts/a11y_audit.py` rewrote docs/ACCESSIBILITY.md without its "needs review" footnote and re-run hint; the generator now writes them, so a re-run no longer loses text.
- ruff 0; mypy clean (53 files); tests/test_scripts.py 11 passed; eslint 0; tsc 0. Full pytest (347) unchanged since 10:00.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: docs proofreading pass (README, WRITEUP, SUBMISSION against the official form fields) and demo caption timing review; keep e2e/a11y/load runs sequential.

## Re-verification 2026-11-01 11:20 WIB (scheduled re-run, form-rule tests and caption timing)
- New `tests/test_submission_rules.py` (6 cases): demo video within the 3:00 limit (now 2:45.5), every caption ordered, inside the video and under 8 s, reading speed at most 28 characters per second, tagline at most 100 characters, the 14 form fields listed in order in `docs/SUBMISSION_FORM.md`, every Meta model id the code calls named in `docs/SUBMISSION.md`.
- Finding: the last caption ran 1.1 s past the end of the video because piece durations were nominal, not measured. `scripts/make_demo_video.py` now uses each clip's probed length for voice-over and captions (so they cannot drift), and prints where a browser recording failed. The shipped SRT and VTT were clamped to the video end; the next full render will also remove the up-to-1.5 s drift.
- A full re-render was attempted three times and not completed: it ran while another job was rebuilding api/ and web/ and running two pytest workers on the same 2 vCPU dev box, and the first attempts lacked sample films in the gallery (the render step timed out at "Contoh · Sample"). `work/demovideo.sh` now seeds the three sample films first (no delay), then records with FAKE_META_DELAY=1.2. Re-render once no other session is active.
- ruff 0 and mypy clean on the touched files; tests/test_submission_rules.py and tests/test_demo_assets.py 15 passed.

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. Next: when no other run is active, run `bash work/demovideo.sh` for a drift-free render (then `scripts/demo_storyboard.py`, kit rebuild, Drive sync); keep e2e/a11y/load runs sequential.

## Verification 2026-11-01 14:25 WIB
Features added this round (commits d885dbd..db369f3, all on the fake Meta API, placeholder art):
- Penjaga Budaya cultural-review agent (Muse Spark + content/cultural_rules.json; fixes scenes before drawing; shown in the trace), character-consistency score from the SAM 3.1 cut-outs, Meta models receipt (calls, tokens, estimated cost) on the film page and `/api/jobs/{id}/receipt` (d885dbd).
- Placeholder testimonials hidden on the live site by default (2f48c5e); submission texts and tagline "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film." (89a09ca, 00ba9ea share card + poster).
- Story Starters: 8 public-domain Nusantara folk tales in id/jv/en (055e807); read-along karaoke captions under the players (c349fa6); printable A5 storybook PDF (c280fa0); /judge 60-second guide and /guru teacher one-pager (70f4e62); evaluation script `scripts/eval.py` (d4415b1, 6/6 golden stories).
- Demo video v2 script (5758158, db369f3) and teasers.

Demo video (rendered 13:20-13:47 WIB from a fresh browser recording, `scripts/demo_local.sh`, fake Meta API):
- `docs/demo/dalang-ai-demo.mp4`: 1920x1080 H.264 + AAC, 173.2 s (2:53), 13 shots. Stand-in child voice (synthetic, labelled on screen) in the first 3.2 s, then the film opening (no 9 s text card), gara-gara choice, second film clip, why, Story Starters, progress, Penjaga Budaya and the models receipt in the trace, storyboard, share page with read-along highlighting, print, close card with "Live app link: added after deploy (PLACEHOLDER)" and "github.com/ragilmalik/dalang-ai (planned)".
- `docs/demo/teaser_60s.mp4` 1920x1080, 60.0 s; `docs/demo/teaser_vertical.mp4` 1080x1920, 40.0 s; both cut from the same render.
- Stills checked by eye at 16 points: captions spelled correctly; known cosmetics: the close card's last line sits under the final burned caption for ~2 s, and in the placeholder film the gunungan's stick crosses one in-film caption word.

Checks:
- ruff 0; mypy clean (56 files); pytest 380 passed (660 s); eslint 0; tsc 0; next build exit 0.
- `scripts/e2e_local.sh`: 26/26 passed (film 64.8 s and gara-gara film 69.8 s).
- `scripts/a11y_local.sh`: axe 14 page checks, 0 violations, 0 serious/critical (needed CHROME=/tmp/bin/chromium on this dev box).
- facts.json: 380 tests, demo 173.2 s, e2e 26/26; coverage 99% is carried from the last measured run (not re-measured this round).

## Verification 2026-11-03 14:15 WIB (scheduled re-run, full re-run on the Nov 3 tree)
- pytest 511 passed in 11m44s on my shared 2 vCPU dev box, api coverage 96% (4973 statements, 199 missed). ruff 0, mypy clean, `scripts/facts.py --check` clean, eslint 0, tsc 0.
- No code changed in this run; the tree matches commit 4e23e3b.

## Verification 2026-11-03 15:05 WIB (scheduled re-run)
- Added `TRUSTED_PROXY_HOPS` (default 0 keeps the old rule): with N proxies of ours in front, the hourly film limit counts the address the Nth proxy saw, so typed fake X-Forwarded-For entries share one bucket. The hourly table is pruned past 5000 addresses. New `tests/test_client_ip.py` (8 tests), `.env.example` and a GO_LIVE section.
- pytest 519 passed in 8m58s, ruff 0, mypy clean, eslint 0, tsc 0, `scripts/facts.py --check` clean (tests 511 to 519; coverage 96% carried from the Nov 3 14:15 run).

### Next up
1. Meta key, then `python scripts/check_keys.py`, then re-render the demo (`scripts/demo_local.sh`).
2. Public repo, deploy, video upload, Cerebral Valley form, X post (see `docs/SUBMISSION_CHECKLIST.md`).
3. After deploy: set `TRUSTED_PROXY_HOPS` to the real proxy count. Still open from the Nov 3 security audit: the 725 KB home page on 3G.

## 2026-11-06: smoother site

What changed: page transitions (`web/app/template.tsx`), poster-to-player morph, loading skeletons for gallery and
Pentas, recorder sound and touch cues with a 90 s ring and a double-tap guard, progress and vote bars on `scaleX`.
How I verified it: build, e2e smoke 29/29, browser 30/30 including four new checks, axe 22/0, pytest 531, tsc,
eslint, ruff, mypy. I looked at the recording state at 390 px by eye. No backend file changed, so no paid API call
was made and spend stays at $2.527.

## 2026-11-06: polish and wording pass

What changed: 800 px WebP poster cards for the gallery and Pentas, layout-shift fixes (every page under 0.1), 44 px
tap targets, puppet images with a size, a light browser bar in day mode, day mode in the accessibility audit, and a
wording pass over every doc and comment with `scripts/voice_check.py` (0 hits) and `tests/test_voice_check.py`.
How I verified it: build, e2e smoke 29/29, browser 30/30, axe 33/0, pytest 546 with 95% line coverage of `api/`,
tsc, eslint, ruff, mypy, `scripts/facts.py --check`. No paid API call was made; spend stays at $2.527.
The Cerebral Valley form is closed (event page: "Event Finished"), so nothing was submitted.
