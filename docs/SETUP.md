# Setup

Everything you need to run Dalang AI on your own computer or a server. Last checked 2026-11-05.

## What you need

* Python 3.10 or newer, Node.js 20 or newer, ffmpeg (the Python package `imageio-ffmpeg` brings one if ffmpeg is
  not installed).
* Internet, for the narration voice (edge-tts) and for the Meta Model API.
* A Meta Model API key from dev.meta.ai, to make new films. Without it you can still watch the three sample films.

## Quick start

```bash
git clone <repo> dalang-ai && cd dalang-ai
bash start.sh            # Windows: double-click start.bat
```

The first start makes `.venv`, installs Python and web packages and builds the website (3 to 5 minutes). Then open
http://localhost:3000. The API runs on http://localhost:8000 (`/docs` lists every endpoint).

## The key

Put the key in the process environment or in `.env` in the repo root (`.env` is git-ignored; copy `.env.example`):

```
META_API_KEY=...
```

`MODEL_API_KEY` works too (the name Meta's docs use). Never commit the key. On a host (Render, Vercel, Docker) set it
in the dashboard or with `-e`.

Check it: `python scripts/go_live.py --preflight` makes one cheap call per model (about $0.02) and prints PASS or
FAIL with a fix for each. If you are behind a proxy, set `HTTPS_PROXY` (and `SSL_CERT_FILE` for a private CA); the
client honours both.

## Modes

| `GET /api/health` → `mode` | When | What happens |
|---|---|---|
| `live` | a key is set | real Meta models; spend is capped (below) |
| `fake` | `FAKE_META=1` | built-in fake Meta API, labelled placeholder art, no cost (tests, CI, offline) |
| `not_configured` | no key, no `FAKE_META` | sample films play; new films get a clear 503 message |

`GET /api/ready` is the readiness probe for a load balancer (503 until the server can make films).

## Settings you may want

| Setting | Default | What it does |
|---|---|---|
| `MAX_USD_PER_FILM` | 1.50 | stops one film's Meta spend at this amount |
| `MAX_USD_TOTAL` | 25 | stops all Meta spend at this total (kept in `data/spend_total.json`) |
| `BUNDLED_SAMPLES` | 1 | copy the three shipped sample films into the gallery on first start |
| `PUBLIC_BASE_URL` | empty | the deployed website address; used for QR codes in films and the kit |
| `LOG_FORMAT` | text | `json` for one JSON object per log line |
| `LOG_LEVEL` | INFO | standard Python log levels |
| `ENCODE_DIR` | empty | encode MP4s on this local folder first (for network filesystems that break ffmpeg's trailer write) |
| `RATE_LIMIT_PER_HOUR`, `MAX_ACTIVE_JOBS` | see `.env.example` | abuse limits for a public server |
| `TRUSTED_PROXY_HOPS` | 0 | how many of your proxies sit in front of the API (see GO_LIVE.md) |
| `USE_OPEN_WEIGHTS`, `BASETEN_API_KEY`, `GLIMMER_API_KEY` | off | optional open-weights stages (OPEN_WEIGHTS.md) |
| `TTS_ENGINE` | auto | narrator engine (VOICES.md) |

The full list with comments is in `.env.example`.

## Running the checks

```bash
pip install -r requirements-dev.txt
ruff check api scripts tests && mypy api scripts && pytest -q -n 2
cd web && npm run lint && npm run typecheck && npm run build
bash scripts/e2e_local.sh      # API + website on the fake API, smoke test and browser checks
bash scripts/a11y_local.sh     # axe-core accessibility audit
```

Tests always run on the fake Meta API (`tests/conftest.py` clears the key), so they cost nothing.

## Re-making the sample films

```bash
python scripts/seed_gallery.py --live                     # live models, into DATA_DIR (about $0.25-0.40 each)
python scripts/bundle_samples.py --data data              # copy the finished films into content/samples/
```

## Deploying

* API: `render.yaml` (Docker, `Dockerfile.api`), health check `/api/health`, readiness `/api/ready`.
* Website: `web/vercel.json`; set `API_ORIGIN` to the API's address before `npm run build`.
* One container for both: `Dockerfile`.

After deploying, set `PUBLIC_BASE_URL` and `TRUSTED_PROXY_HOPS` (GO_LIVE.md).
