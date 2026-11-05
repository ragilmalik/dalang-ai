#!/bin/bash
# One-shot demo render: seed the 3 sample films, start fake-Meta API :8000 (slowed so the progress screen is
# watchable) + Next.js :3000, run scripts/make_demo_video.py, stop both. Needs `cd web && npm run build` first.
# Do not run at the same time as scripts/e2e_local.sh (different ports, but both use their own DATA_DIR; CPU).
R="$(cd "$(dirname "$0")/.." && pwd)"
cd "$R"
export FAKE_META=1 DATA_DIR=/tmp/dalang-demo-data NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
rm -rf /tmp/dalang-demo-data
.venv/bin/python scripts/seed_gallery.py || exit 1
FAKE_META_DELAY=${FAKE_META_DELAY:-1.2} .venv/bin/python -m uvicorn api.main:app --port 8000 > /tmp/demo-api.log 2>&1 &
API=$!
(cd web && exec setsid npx next start -p 3000 > /tmp/demo-web.log 2>&1) &
WEB=$!
for i in $(seq 1 90); do curl -sf --noproxy '*' http://127.0.0.1:8000/api/health >/dev/null && break; sleep 1; done
for i in $(seq 1 60); do curl -sf --noproxy '*' http://127.0.0.1:3000/api/health >/dev/null && break; sleep 1; done
.venv/bin/python scripts/make_demo_video.py http://127.0.0.1:3000 "$@"
RC=$?
echo "demo exit $RC"
kill $API 2>/dev/null
kill -- -$WEB 2>/dev/null || kill $WEB 2>/dev/null
exit $RC
