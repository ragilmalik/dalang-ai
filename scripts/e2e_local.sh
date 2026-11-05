#!/bin/bash
# One-shot local e2e: fake-Meta API :8000 + Next.js :3005 + scripts/smoke_test.py, then stops both.
# Needs `cd web && npm run build` first. Run: bash scripts/e2e_local.sh
R="$(cd "$(dirname "$0")/.." && pwd)"
# API_PORT / WEB_PORT / DATA_DIR override the defaults, e.g. when another copy runs on the same machine; the web
# build must then proxy to that API port: API_ORIGIN=http://127.0.0.1:$API_PORT NEXT_DIST_DIR=.next-x npx next build,
# and the same NEXT_DIST_DIR set here.
API_PORT=${API_PORT:-8000} WEB_PORT=${WEB_PORT:-3005}
export API_ORIGIN=${API_ORIGIN:-http://127.0.0.1:$API_PORT}  # the server-rendered pages (watch, judge) fetch the API at run time
cd $R
export FAKE_META=1 DATA_DIR=${DATA_DIR:-/tmp/dalang-e2e} NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
rm -rf "$DATA_DIR"
.venv/bin/python -m uvicorn api.main:app --port $API_PORT > /tmp/e2e-api.log 2>&1 &
API=$!
(cd web && exec setsid npx next start -p $WEB_PORT > /tmp/e2e-web.log 2>&1) &
WEB=$!  # own process group, so next-server and its children stop together even without `ss`
for i in $(seq 1 90); do curl -sf --noproxy '*' http://127.0.0.1:$API_PORT/api/health >/dev/null && break; sleep 1; done
for i in $(seq 1 60); do curl -sf --noproxy '*' http://127.0.0.1:$WEB_PORT/api/health >/dev/null && break; sleep 1; done
timeout 900 .venv/bin/python scripts/smoke_test.py http://127.0.0.1:$WEB_PORT 2>&1 | tee /tmp/dalang-e2e.log
RC=${PIPESTATUS[0]}
# the newer web screens in a real browser (Kelir Live drag, vote, remix, /pentas, PWA): web/e2e/r5_ui.py
timeout 900 .venv/bin/python web/e2e/r5_ui.py http://127.0.0.1:$WEB_PORT 2>&1 | tee /tmp/dalang-e2e-web.log
WRC=${PIPESTATUS[0]}
[ $RC -eq 0 ] && RC=$WRC
# a passing run updates the e2e count the docs quote (docs/facts.json, see scripts/facts.py)
[ $RC -eq 0 ] && .venv/bin/python scripts/facts.py --no-measure --e2e-log /tmp/dalang-e2e.log
echo "smoke exit $RC"
kill $API 2>/dev/null
kill -- -$WEB 2>/dev/null || kill $WEB 2>/dev/null
P=$(ss -ltnp 2>/dev/null | grep ":$WEB_PORT " | grep -o 'pid=[0-9]*' | cut -d= -f2); [ -n "$P" ] && kill $P
exit $RC
