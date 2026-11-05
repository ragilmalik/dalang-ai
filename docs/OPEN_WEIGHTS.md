# Open-weight models in Dalang AI

Checked against Meta's docs on 2026-10-31 (sources below). Nothing here is invented: every model string and
endpoint is the one the docs publish.

| Model | What it does in Dalang AI | Where it runs | Model string | Switch |
|---|---|---|---|---|
| **Muse Spark Open** | Writes the lakon (script) instead of hosted Muse Spark | Baseten, OpenAI-compatible, `https://inference.baseten.co/v1` | `meta-models/muse-spark-open` (`OPEN_MODEL`) | `USE_OPEN_WEIGHTS=true` + `BASETEN_API_KEY` |
| **Muse Glimmer** (30B, Apache 2.0) | Child-safety screen (story and gara-gara answers) and the title/moral polish | Together AI, OpenAI-compatible, `https://api.together.xyz/v1`; or any self-hosted OpenAI-compatible server (vLLM, SGLang, llama.cpp, Ollama, LM Studio) | `meta-models/Muse-Glimmer-30B` on Together (`GLIMMER_MODEL`); `muse-glimmer` on a self-hosted server | `USE_OPEN_WEIGHTS=true` + `GLIMMER_API_KEY` (or `TOGETHER_API_KEY`), or `GLIMMER_API_BASE=http://localhost:8000/v1` |

## Switch it on (one environment variable)

```bash
# try the open-weights route for free on the built-in fake API (no keys): the lakon request goes to the
# Baseten URL with the Muse Spark Open model string, and the safety screen + polish go to Muse Glimmer
FAKE_META=1 USE_OPEN_WEIGHTS=true bash start.sh
curl -s localhost:8000/api/health   # "open_weights": true, "models": {"lakon": "meta-models/muse-spark-open", ...}

# live: put these in .env (I still have to add the keys; nothing is spent until they exist)
USE_OPEN_WEIGHTS=true
BASETEN_API_KEY=...          # Muse Spark Open writes the lakon
GLIMMER_API_KEY=...          # optional: Muse Glimmer on Together AI (or GLIMMER_API_BASE=http://localhost:8000/v1)
```

With `USE_OPEN_WEIGHTS=true` but no Baseten key and a Meta key set, the lakon stays on hosted Muse Spark
(`settings.open_weights_active` needs the key), so the switch can never break a live demo. A film made on the open
route lists `meta-models/muse-spark-open` (open weights) in its model list and agent trace.

## Muse Spark Open: what the docs say and how we follow it
* Model string on Baseten: `meta-models/muse-spark-open`, OpenAI-compatible chat completions at
  `https://inference.baseten.co/v1` ([deploy on Baseten](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten)).
  A dated id from the Baseten dashboard can go in `OPEN_MODEL`; no other id is assumed.
* Request: the same messages and `json_schema` response format as hosted Muse Spark, `max_tokens` 16384
  (reasoning and answer share the budget), `reasoning_effort`; if the provider only takes `json_object`, the call
  retries with it, and the reply is validated with pydantic (one retry with the error) like every other model.
* Code: `api/config.py` (`USE_OPEN_WEIGHTS`, `BASETEN_API_KEY`, `OPEN_API_BASE`, `OPEN_MODEL`),
  `api/meta_client.py` (`chat_json(..., open_weights=True)`), `api/pipeline/lakon.py`, `api/fake_meta.py` (refuses
  any other model string on the Baseten host).
* Tests (fake API, no keys): `tests/test_open_weights.py` checks the exact URL, model string, schema and token
  budget of the lakon request, that the film records the open model, that `/api/health` reports it, and that the
  environment variable alone turns the route on and off in a fresh process.

## Muse Glimmer: what the docs say and how we follow it
* Muse Glimmer is open-weight and is **not** served on Meta Model API; you run it yourself or call a hosted
  provider ([models](https://dev.meta.ai/docs/models), [overview](https://dev.meta.ai/docs/muse-glimmer)).
* The documented hosted provider is **Together AI**, model string `meta-models/Muse-Glimmer-30B`, OpenAI
  chat-completions wire format at `https://api.together.xyz/v1/chat/completions`
  ([run inference, hosted providers](https://dev.meta.ai/docs/muse-glimmer/deploy#hosted-providers)).
  Baseten also lists a Muse Glimmer 30B deployment in its model library; it is a dedicated deployment with its
  own model id, so it is reachable through the same `GLIMMER_API_BASE` / `GLIMMER_MODEL` settings, but Meta's
  docs table names only Together AI.
* Self-hosted servers answer to `"model": "muse-glimmer"` (`--served-model-name muse-glimmer`).
* The model reasons before it answers: we give `max_tokens` 8192 of headroom. We never send `temperature: 0`
  (the docs warn greedy decoding loops) and we do not send `reasoning_effort` (llama.cpp ignores it and the
  ExecuTorch server rejects it). Structured output asks for `json_schema` and falls back to `json_object`, and the
  JSON is then validated with pydantic like every other model reply.
* Code: `api/meta_client.py` (`chat_json(..., glimmer=True)`), `api/pipeline/listen.py` (`screen`),
  `api/pipeline/lakon.py` (`polish`), `scripts/check_keys.py` (Glimmer check), `api/fake_meta.py` (fake route),
  `tests/test_glimmer.py`.
* The UI labels both models "(open weights)" on the home page and in a film's model list.

Status: implemented and tested on the built-in fake API only. A live call needs a Together AI key (paid per token,
$0.35 / $1.50 per million input / output tokens on Together's page) or a local GPU server; I have neither yet.
