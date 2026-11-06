# Go-live day: the first real Meta key

Plain steps for the day the Meta Model API key arrives. Nothing here spends money until step 3.

1. Paste the key after `META_API_KEY=` in the `.env` file in the repo root.
2. Optional caps (already safe by default): `MAX_USD_PER_FILM=1.50` stops any one film at $1.50,
   `MAX_USD_TOTAL=25` stops all real Meta spending at $25 in total (kept in `data/spend_total.json`).
3. Run `make preflight` (or `python scripts/go_live.py --preflight`). It makes **one** of the cheapest possible
   calls per Meta model (1 second of audio, a tiny JSON answer from Muse Spark 1.3 / 1.2 and Muse Wonder, one
   small Muse Image picture, one SAM 3.1 cut-out): about **$0.02** in total. Each request is first checked against
   Meta's documented shapes; a malformed one is refused on this computer and never sent.
4. Read the table. Every line says PASS or FAIL; under a FAIL there is one sentence saying what to do
   (key refused, model not enabled for the app, rate limited, spend cap reached, or "tell the developer").
5. Optional, to rehearse for free afterwards: run once with `META_RECORD_DIR=fixtures/` set, then use
   `META_REPLAY_DIR=fixtures/` for every rehearsal after; replay answers from the recorded real replies with no
   network and no cost. Recordings never contain the key; images and audio in the requests are stored as hashes.

`make preflight-dry` shows the same table on the built-in fake API, so you can see what it looks like first.

## What happened on Nov 5, 2026 (the first real key)

* Preflight 6/6 PASS, about $0.015, after one fix: the first run got HTTP 401 on every model because the preflight
  built its own HTTP transport and skipped the proxy settings. `meta_client.real_transport()` fixed it.
* Three sample films made end to end on the live models (91 calls, none failed, $0.26 to $0.36 each). They are in
  `content/samples/` and load into the gallery on first start.
* Things only the real models showed: SAM 3.1 needs plain nouns ("deer", "person") more than the word "puppet";
  Muse Spark 1.3 can return no content when its token budget goes to reasoning; ffmpeg needs `ENCODE_DIR` on a
  network drive. Details and numbers: [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).
* The key only ever lived in the process environment. Run the API with `META_API_KEY` set in the shell (or `.env`,
  which is git-ignored); nothing writes it to a file or a log, and `api/logs.py` scrubs anything that looks like one.

If a model has a bad day during the demo: Muse Image failures become pictures labelled "placeholder" (the film still
finishes), a failing picture checker keeps the picture, Muse Wonder and the Director fall back to rule-based motion,
and a model that fails four times in a row is paused for a minute (its "circuit" opens) instead of being hammered.
`GET /api/health` shows each model's circuit state and the money spent so far. Measured on the fake API with
injected failures: see "Failure test" in [EVAL_REPORT.md](EVAL_REPORT.md).

See also: [META_MODELS.md, "Go-live safety net"](META_MODELS.md#go-live-safety-net) (contract tests,
retries, breaker, caps, fixtures in detail) · [MALIK_CHECKLIST.md](MALIK_CHECKLIST.md) (claiming the credits, the
full `go_live.py` run that re-renders the demo with real art, deploying) · [DEMO_SCRIPT.md](DEMO_SCRIPT.md) (what
the re-rendered demo shows) · [README](../README.md#added-nov-1-2).

## One setting after you deploy: TRUSTED_PROXY_HOPS

The hourly film limit counts visitors by address. Out of the box it trusts the first `X-Forwarded-For` address, which
is right for one proxy but lets someone type fake addresses to get new buckets. Once the app is live, check how many
proxies of yours sit in front of the API (for example Vercel, then Render) and set `TRUSTED_PROXY_HOPS` to that
number in the API's environment. Then only the address your own last proxy saw counts. The films-in-progress cap
and the spend caps hold either way.

## Narrator voice when deployed (optional Kokoro)

Nothing to do for the voice by default. The Docker image installs only `requirements.txt`, so every film is narrated
by edge-tts (Indonesian and English by `en-US-EmmaMultilingualNeural`, Javanese by `jv-ID-SitiNeural`). That needs
internet but no key.

Kokoro-82M is the nicer English narrator (it won the listening test in [VOICES.md](VOICES.md)). It's optional and
adds about 1 GB, so it isn't in the image. To turn it on:

* On your own computer: `pip install torch --index-url https://download.pytorch.org/whl/cpu`, then
  `pip install -r requirements-tts.txt`, and install `espeak-ng` (apt or brew). Restart the app. `TTS_ENGINE`
  stays `auto` (the default), which uses Kokoro for English whenever it can be imported.
* Or keep it in its own venv and set `TTS_PYTHON=/path/to/that/venv/bin/python` in `.env`.
* On Render: add `espeak-ng` to the `apt-get install` line in `Dockerfile.api` and
  `RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements-tts.txt`
  after the `requirements.txt` line (copy `requirements-tts.txt` in too). The Starter plan's RAM is enough for
  Kokoro; MMS is not needed.

If Kokoro is missing or fails, that line falls back to edge-tts by itself. `TTS_ENGINE=edge` forces edge-tts
everywhere. `TTS_ENGINE=mms` (Meta MMS-TTS) is opt-in only, because its licence is CC-BY-NC-4.0 (non-commercial).
