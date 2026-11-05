#!/usr/bin/env bash
# Start Dalang AI (backend on :8000, website on :3000). macOS / Linux:  bash start.sh
set -e
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
if [ ! -d .venv ]; then
  echo "First run: installing (a few minutes)..."
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi
if [ ! -d web/node_modules ]; then (cd web && npm install --no-audit --no-fund); fi
if [ ! -d web/.next ]; then (cd web && npm run build); fi
.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
echo ""
echo "  Dalang AI is starting. Open http://localhost:3000 in your browser."
echo ""
cd web && npm run start
