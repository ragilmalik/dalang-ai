# Handoff

For whoever picks this up next (me later on, or a teammate).

## State (numbers from `docs/facts.json`, refreshed by `python scripts/facts.py`)
* Feature-complete against SPEC.md. Runs on the live Meta Model API since Nov 5, 2026 (preflight 6/6 PASS; per-model
  results, latency and cost in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md)). `FAKE_META=1` is test mode only; a
  server without a key refuses new films with a 503 instead of faking them.
* Three sample films made with the live models ship in `content/samples/` and load on first start
  (`api/samples.import_bundled`, `BUNDLED_SAMPLES=false` to skip). `scripts/bundle_samples.py --data <data dir>`
  refreshes them from a data folder.
* Checks: pytest (<!-- facts:tests -->557<!-- /facts --> tests, <!-- facts:coverage -->95%<!-- /facts --> line coverage), full-stack e2e smoke test (<!-- facts:e2e -->29/29<!-- /facts --> steps), ruff, mypy, eslint, tsc, `next build` (see TEST_REPORT.md).
* The public repo is a clean export (one commit per release, no `.env`, scanned with gitleaks before each push); the
  full dated history stays on my machine because it holds old demo cuts. CI is in `.github/workflows/ci.yml`; deploy
  blueprints are `render.yaml` (backend) and `web/vercel.json` (website).
* Since Nov 6 everything judges see was recorded on the live API: demo video, teasers, launch clips, thumbnail and
  every screenshot (VERIFICATION_REPORT.md, "Media re-recorded on the live API"). The narrator is a synthetic voice,
  and the child's voice in the demo's first 3 s is a labelled synthetic stand-in.
* The Cerebral Valley form closed before I submitted (Nov 6: "Event Finished"); the answers stay ready in
  [SUBMISSION_FORM.md](SUBMISSION_FORM.md).
* Live spend so far: about $2.53 of the $15 credit (`MAX_USD_TOTAL` stops all Meta calls at the cap in `.env`).

## What is real and what isn't
* Real: every Meta model call behind the sample films, the demo, the screenshots and the trace; the art (Muse Image),
  cut-outs (SAM 3.1), scripts (Muse Spark), motion plans (Muse Wonder), transcription (Muse Voice Transcribe).
* Synthetic, and labelled as such: the narration voices (Meta has no TTS model), the demo narrator, the sample story
  recording, the three classroom "phones" in the demo's vote shot (API calls from the recording script).
* Not done yet: family testing, a cultural review by a dalang, a native Javanese check, a deployed live link and QR.

## Links (filled in when they exist)
* Repo: https://github.com/ragilmalik/dalang-ai
* Live app: not deployed yet
* Demo video: not uploaded yet

## How the pieces fit
* `web/` (Next.js 16, App Router, Tailwind 3) talks only to `/api/*` and `/media/*` on its own origin; `next.config.mjs` rewrites them to the Python API. **The rewrite target (`API_ORIGIN`, default `http://127.0.0.1:8000`) is fixed when `npm run build` runs**; rebuild if you move the API.
* The look comes from one design system: tokens in `web/app/globals.css` + `web/tailwind.config.ts`, components in `web/components/ui/`, fonts (Fraunces, Plus Jakarta Sans, OFL) in `web/app/fonts/`. Use the token names, not raw hex. Reasons and rules: [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md). `python web/e2e/ui_shots.py` re-shoots every page (phone 390, desktop 1440) into `docs/screenshots/ui/after/`.
* `api/main.py` (FastAPI) creates jobs, streams state over SSE (ends at review/done/failed/blocked; the browser reconnects), serves media.
* `api/runner.py` runs stages in a 2-worker thread pool; each job has a cost meter (`api/cost.py`), errors become `failed` (or a DEMO_MODE replay), safety blocks become `blocked`.
* `api/jobs.py` holds job state (JSON in SQLite, `api/db.py`); every change bumps a version that SSE watches.
* `api/meta_client.py` is the only module that calls Meta/Baseten. `client()` returns an httpx client; with `FAKE_META=1` (tests, rehearsals) it is wired to `api/fake_meta.py`, an httpx MockTransport that answers the same documented endpoints with fixtures and procedural placeholder art.
* Logs: `api/logs.py` (request id via `X-Request-ID`, job id per film, stage timings, `LOG_FORMAT=json`, secrets scrubbed). `/api/ready` checks the database, storage, ffmpeg and that Meta's `/v1/models` answers.
* Pipeline: `listen → lakon → casting(+segment, +verify) → scenes(+verify)` then, after optional review, `animate → narrate → cut`. `engine.py` is the renderer (keyframe interpolation, idle sway/tremble, lamp flicker, shadows, gunungan wipes, captions, title/end cards) streaming raw frames into ffmpeg.

## Decisions and why
* Muse Wonder plans motion instead of rendering video: Meta has no video model (docs, 2026-10-30).
* Verify agent uses Muse Spark 1.3 vision (SPEC §5.8); Muse Wonder is used where its strength (multimodal planning) matters.
* Narration voices live in `api/tts.py`: no Meta TTS. edge-tts needs no key and covers all three languages; Kokoro-82M (optional, `requirements-tts.txt`) is the English default when installed. The Nov 2 shoot-out and how to rerun it: [VOICES.md](VOICES.md).
* Javanese speech goes to Muse Spark 1.2 audio: Voice Transcribe does not list Javanese.
* Open-weights id defaults to the documented `meta-models/muse-spark-open`; override with `OPEN_MODEL`.
* Image cache by prompt hash and lakon cache by transcript hash keep rehearsals cheap; repaint adds a variation nudge to bypass the cache.

## Gotchas
* Live SAM 3.1 often finds nothing for "puppet" but finds plain nouns ("deer", "person"); `segment.queries()` tries them in order. The gunungan never gets a mask and uses the background cut-out.
* On a network filesystem ffmpeg can fail writing the MP4 trailer; set `ENCODE_DIR` to a local folder.
* `meta_client.real_transport()` is the only way to build a raw transport: a hand-built `httpx.HTTPTransport()` ignores `HTTPS_PROXY` / `SSL_CERT_FILE` (that gave 401s on the first live preflight).
* The fake Meta API scripts one checker rejection (scene 2 backdrop) so the redraw loop shows in demos and tests; images drawn from the checker's fix prompt are recognised by a tiny fingerprint and pass.
* The phone microphone needs https (or localhost). Use a cloudflared tunnel for phone demos.
* Behind an authenticated proxy, edge-tts can fail to parse the proxy URL; `media.narrate` retries without proxy variables. On a normal computer this never triggers.
* Muse Wonder can return a keyframe number just outside the stage limits (seen live: an angle past 25 degrees).
  `animate.clamp_motion` clamps instead of dropping the plan; anything structurally wrong still falls back.
* Element screenshots of the agent trace get the sticky site header painted over them; make the header static
  first (`work/live/extra_shots.py` does).
* `pkill -f <pattern>` inside a shell whose own command line contains the pattern kills that shell (bit us during testing).
* The prompt docs (`docs/prompts.md`) are generated from `api/prompts.py`; regenerate after editing prompts.

## Where to start reading
`README.md` → `docs/architecture.png` → `api/runner.py` → `api/pipeline/*.py` → `api/meta_client.py`.
