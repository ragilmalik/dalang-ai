# Architecture

How Dalang AI is put together, as of 2026-11-05. For setup see [SETUP.md](SETUP.md); for how each Meta model is
used see [META_MODELS.md](META_MODELS.md).

## The parts

```
browser ──> web/ (Next.js, port 3000) ──/api, /media──> api/ (FastAPI, port 8000) ──> api.meta.ai (Meta Model API)
                                                         │                         └─> Baseten / Together AI (optional open weights)
                                                         ├─ SQLite (data/dalang.db): one row per film, state as JSON
                                                         ├─ data/jobs/<id>/: pictures, puppets, narration, final MP4s
                                                         └─ ffmpeg + the kelir renderer (api/pipeline/engine.py)
```

* **web/** is a Next.js App Router site. It never talks to Meta. It proxies `/api/*` and `/media/*` to the API
  (`API_ORIGIN`, default `http://127.0.0.1:8000`), so the browser sees one origin.
* **api/** is one FastAPI process. A film is a background job on a small thread pool (`api/runner.py`); its state
  is saved to SQLite on every change and pushed to the browser over Server-Sent Events (`/api/jobs/{id}/events`).
* **api/meta_client.py** is the only module that sends requests to Meta. Every call goes through one `_post` with
  retries (429/5xx, timeouts, `Retry-After`), a per-model circuit breaker, a per-film and a total spend cap
  (`MAX_USD_PER_FILM`, `MAX_USD_TOTAL`), and a line in the film's agent trace.

## A film, stage by stage

| Stage | Code | Model |
|---|---|---|
| Listen | `pipeline/listen.py` | Muse Voice Transcribe (`/v1/asr/transcribe`, ENDPOINTING); Basa Jawa audio goes to Muse Spark 1.2 `input_audio` |
| Safety screen | `pipeline/listen.py` | Muse Spark 1.3 structured output |
| Lakon (script) | `pipeline/lakon.py`, `prompts.py` | Muse Spark 1.3 `response_format: json_schema`, validated with Pydantic (`schemas.py`) |
| Cultural review | `pipeline/penjaga.py` | Muse Spark 1.3 against `content/cultural_rules.json` |
| Casting | `pipeline/casting.py` | Muse Image `/v1/images/generations`, one sheet per character |
| Cut-out | `pipeline/segment.py`, `pipeline/puppet.py` | SAM 3.1 `/v1/responses` (streamed masks, `meta-sam-parser`); plain-background key as fallback |
| Scenes | `pipeline/scenes.py` | Muse Image backdrops; puppets composited on their marks |
| Verify | `pipeline/verify.py` | Muse Spark 1.3 vision checks each picture; a failed picture is redrawn up to 2 times |
| Director, motion | `pipeline/director.py`, `pipeline/animate.py` | Muse Spark 1.3 plans camera/transitions; Muse Wonder returns keyframes per scene |
| Narrate | `pipeline/narrate.py`, `tts.py` | edge-tts / Kokoro (Meta's API has no text-to-speech) |
| Final cut | `pipeline/cut.py`, `pipeline/engine.py` | ffmpeg; 16:9 and 9:16 MP4, captions, poster |

Muse Wonder outputs text, not video: the motion is rendered by our own engine from its keyframes.

## Modes

`GET /api/health` reports `mode`:

* **live**: `META_API_KEY` (or `MODEL_API_KEY`) is set and `FAKE_META` is off. Every call goes to api.meta.ai.
* **fake**: `FAKE_META=1`. Every call is answered by `api/fake_meta.py` with recorded fixtures and labelled
  placeholder art. Used by the tests, CI and offline rehearsals. The request and parsing code is the same as live.
* **not_configured**: no key and no `FAKE_META`. The gallery and the bundled sample films work; anything that would
  call a model answers 503 with a plain message. The server never fakes output silently.

`GET /api/ready` answers 200 only when the database and data folder are writable, ffmpeg is present and, in live mode,
api.meta.ai answers `GET /v1/models` and lists every model the pipeline uses (cached 60 s).

## Sample films

The three sample films (Kancil in Bahasa Indonesia, Timun Mas in Basa Jawa, The Golden Snail in English) are sample
stories written for this project (`api/sample_stories.py`), made with the live Meta models on 2026-11-05 and shipped
in `content/samples/<key>/` (state + compressed media, `scripts/bundle_samples.py`). On start the API copies them
into its data folder once (`api/samples.import_bundled`, `BUNDLED_SAMPLES=1` by default). They are labelled
"Contoh · Sample" everywhere and their title card says "contoh cerita / a sample story".

## Logging and errors

`api/logs.py` sets up logging once. Every line carries the request id (from `X-Request-ID`, or a new one, echoed in
the response) and, inside a film's worker thread, the film id. Stage ends are logged with their duration.
`LOG_FORMAT=json` writes one JSON object per line. Messages are scrubbed for anything that looks like a credential,
and the code logs ids, stages, models, timings and status codes, not story text or recordings.

A family never sees a stack trace: `api/errors.py` maps failures to a short bilingual message, unhandled errors on a
request get a 500 with a kind message and the request id, and a film that fails keeps the typed story or the recording for a retry.

## Storage and privacy

* Recordings are deleted after transcription (or once the film is made, when the child's own voice narrates).
* The browser keeps its own copy of the recording (IndexedDB, `web/lib/draft.ts`) only until the film is done, at most
  6 hours, so a film that failed can be sent again without telling the story again. Typed stories stay in the tab the
  same way (sessionStorage).
* Films are private until the family shares them. Old private films can be cleaned up (`CLEANUP_DAYS`).
* `STORAGE_BACKEND=r2` publishes finished MP4s to Cloudflare R2; the default keeps them on local disk.
* `/media` never serves recordings, JSON or the database.

## Deploying

`render.yaml` (API, Docker) and `web/vercel.json` (website). `Dockerfile` runs both in one container. Set the key in
the host's dashboard, never in a committed file. See [GO_LIVE.md](GO_LIVE.md) and [SETUP.md](SETUP.md).
