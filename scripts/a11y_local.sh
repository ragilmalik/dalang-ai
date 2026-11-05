#!/bin/bash
# One-shot accessibility audit: fake-Meta API :8000 + Next.js :3006 + scripts/a11y_audit.py, then stops both.
# Needs `cd web && npm run build` first and a Chromium (scripts/browser_path.py). Not at the same time as e2e_local.sh
# (same API port). Writes docs/ACCESSIBILITY.md.
R="$(cd "$(dirname "$0")/.." && pwd)"
# API_PORT / WEB_PORT / DATA_DIR override the defaults, e.g. when another copy runs on the same machine; the web
# build must then proxy to that API port: API_ORIGIN=http://127.0.0.1:$API_PORT NEXT_DIST_DIR=.next-x npx next build,
# and the same NEXT_DIST_DIR set here.
API_PORT=${API_PORT:-8000} WEB_PORT=${WEB_PORT:-3006}
export API_ORIGIN=${API_ORIGIN:-http://127.0.0.1:$API_PORT}  # the server-rendered pages (watch, judge) fetch the API at run time
cd "$R"
LOG_DIR=${LOG_DIR:-/tmp}  # logs and the throwaway data folder
mkdir -p "$LOG_DIR"
export TZ=${TZ:-Asia/Jakarta} FAKE_META=1 DATA_DIR=${DATA_DIR:-$LOG_DIR/dalang-a11y} NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
rm -rf "$DATA_DIR"
.venv/bin/python -m uvicorn api.main:app --port $API_PORT > $LOG_DIR/a11y-api.log 2>&1 &
API=$!
(cd web && exec setsid npx next start -p $WEB_PORT > $LOG_DIR/a11y-web.log 2>&1) &
WEB=$!
for i in $(seq 1 90); do curl -sf --noproxy '*' http://127.0.0.1:$API_PORT/api/health >/dev/null && break; sleep 1; done
for i in $(seq 1 60); do curl -sf --noproxy '*' http://127.0.0.1:$WEB_PORT/api/health >/dev/null && break; sleep 1; done
timeout 900 .venv/bin/python scripts/a11y_audit.py http://127.0.0.1:$WEB_PORT "$@"
RC=$?
echo "a11y exit $RC"
kill $API 2>/dev/null
kill -- -$WEB 2>/dev/null || kill $WEB 2>/dev/null
exit $RC
