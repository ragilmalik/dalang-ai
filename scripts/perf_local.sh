#!/bin/bash
# Web performance check + sample gallery, one shot: fake-Meta API :8000 with SEED_SAMPLES=1 (3 labelled sample films
# render in the background), Next.js :3006, waits for the samples, runs scripts/web_perf.py (writes docs/WEB_PERF.md
# and the gallery screenshot), then stops both. Needs `cd web && npm run build` first. Run: bash scripts/perf_local.sh
R="$(cd "$(dirname "$0")/.." && pwd)"
cd $R
export FAKE_META=1 SEED_SAMPLES=1 DATA_DIR=/tmp/dalang-perf NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
export RATE_LIMIT_PER_HOUR=0 MAX_ACTIVE_JOBS=0
rm -rf /tmp/dalang-perf
.venv/bin/python -m uvicorn api.main:app --port 8000 > /tmp/perf-api.log 2>&1 &
API=$!
(cd web && exec setsid npx next start -p 3006 > /tmp/perf-web.log 2>&1) &
WEB=$!
for i in $(seq 1 60); do curl -sf --noproxy '*' http://127.0.0.1:3006/api/health >/dev/null && break; sleep 1; done
N=0
for i in $(seq 1 180); do  # up to 15 minutes for the three sample films
  N=$(curl -sf --noproxy '*' http://127.0.0.1:8000/api/gallery | .venv/bin/python -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  [ "$N" -ge 3 ] && break; sleep 5
done
echo "sample films in gallery: $N"
.venv/bin/python scripts/web_perf.py http://127.0.0.1:3006 --shot docs/screenshots/6-gallery.png
RC=$?
echo "web_perf exit $RC"
kill $API 2>/dev/null
kill -- -$WEB 2>/dev/null || kill $WEB 2>/dev/null
exit $RC
