#!/bin/bash
# Concurrency check on the fake Meta API: API on :8010 with a scratch DATA_DIR and MAX_ACTIVE_JOBS=6, then
# scripts/load_test.py starts 6 films at the same moment, then the API is stopped. Safe to run beside e2e (own
# port and data dir). Result: /tmp/dalang-load.json and the exit code.
R="$(cd "$(dirname "$0")/.." && pwd)"
cd "$R"
export FAKE_META=1 DATA_DIR=/tmp/dalang-load MAX_ACTIVE_JOBS=6 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
rm -rf /tmp/dalang-load
.venv/bin/python -m uvicorn api.main:app --port 8010 > /tmp/load-api.log 2>&1 &
API=$!
for i in $(seq 1 90); do curl -sf --noproxy '*' http://127.0.0.1:8010/api/health >/dev/null && break; sleep 1; done
.venv/bin/python scripts/load_test.py http://127.0.0.1:8010 --jobs 6 --limit 6 --out /tmp/dalang-load.json
RC=$?
ERR=$(grep -ciE "traceback|database is locked|readonly database" /tmp/load-api.log)
echo "server log errors: $ERR"
kill $API 2>/dev/null
[ "$ERR" = "0" ] || RC=1
echo "load exit $RC"
exit $RC
