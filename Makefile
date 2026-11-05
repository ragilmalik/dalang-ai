# Dalang AI: one-word commands. `make demo` is the judge path (no keys, free, placeholder art).
PY := .venv/bin/python
.PHONY: help install start demo samples test coverage lint check e2e facts kit ci-lint a11y load demo-video eval preflight preflight-dry

help:  ## list the commands
	@grep -E "^[a-z0-9-]+:.*## " Makefile | sed "s/:.*## /\t/"

install:  ## Python venv + dev tools, web packages
	[ -d .venv ] || python3 -m venv .venv
	.venv/bin/pip install -q -r requirements-dev.txt
	cd web && npm install --no-audit --no-fund

start:  ## run the app (backend :8000 + website :3000), live Meta models if a key is in .env
	bash start.sh

demo:  ## run the app on the fake Meta API (labelled placeholder art); the gallery has the 3 bundled real sample films
	FAKE_META=1 bash start.sh

samples:  ## re-make the 3 sample films with the live Meta models (needs META_API_KEY; costs money)
	$(PY) scripts/seed_gallery.py

test:  ## pytest (fake Meta API, no keys, no cost)
	$(PY) -m pytest -q

coverage:  ## pytest with line coverage of api/; records the number in docs/facts.json
	COVERAGE_CORE=sysmon $(PY) -m pytest -q --cov=api --cov-report=term --cov-report=json:/tmp/dalang-cov.json
	$(PY) -c "import json,subprocess,sys; p=json.load(open(\"/tmp/dalang-cov.json\"))[\"totals\"][\"percent_covered\"]; sys.exit(subprocess.call([sys.executable, \"scripts/facts.py\", \"--coverage\", str(p)]))"

lint:  ## ruff + mypy + eslint + tsc
	.venv/bin/ruff check . && .venv/bin/mypy api scripts
	cd web && npx eslint . && npx tsc --noEmit

check: lint test  ## every check: lint, types, tests, production build
	cd web && npx next build

e2e:  ## full stack: build the website, start API + website, run the smoke test, stop both
	cd web && npx next build
	bash scripts/e2e_local.sh

eval:  ## golden stories + Director, gamelan, Remix, vote, robustness (failure injection) on the fake Meta API -> docs/EVAL_REPORT.md
	$(PY) scripts/eval.py

preflight:  ## go-live check: ONE cheapest call per Meta model, PASS/FAIL table (needs META_API_KEY; about $0.02)
	$(PY) scripts/go_live.py --preflight

preflight-dry:  ## the same preflight table on the fake Meta API (free)
	$(PY) scripts/go_live.py --preflight --dry-run

facts:  ## refresh the numbers the docs quote (tests, demo length) from one source
	$(PY) scripts/facts.py

kit:  ## build the submission kit (../deliverables/submission-kit.zip)
	$(PY) scripts/make_submission_kit.py

ci-lint:  ## validate .github/workflows with actionlint (https://github.com/rhysd/actionlint) if it is installed
	@command -v actionlint >/dev/null || { echo "actionlint not installed: https://github.com/rhysd/actionlint"; exit 1; }
	actionlint .github/workflows/*.yml

a11y:  ## axe-core accessibility audit of the 5 pages (phone + desktop), writes docs/ACCESSIBILITY.md
	cd web && npx next build
	bash scripts/a11y_local.sh

load:  ## 6 films at once on the fake Meta API: all finish, the 7th gets a kind 429, no server errors
	bash scripts/load_local.sh

demo-video:  ## re-render docs/demo/dalang-ai-demo.mp4 from a real browser session on the fake Meta API (go_live.py does the live one)
	cd web && npx next build
	bash scripts/demo_local.sh
