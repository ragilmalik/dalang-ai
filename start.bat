@echo off
REM Double-click to start Dalang AI on Windows. Needs Python 3.10+ and Node.js 20+ installed.
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul
if not exist .venv (
  echo First run: installing, this takes a few minutes...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\pip install -q -r requirements.txt
)
if not exist web\node_modules (cd web & call npm install --no-audit --no-fund & cd ..)
if not exist web\.next (cd web & call npm run build & cd ..)
start "Dalang AI backend" .venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
timeout /t 3 >nul
start "" http://localhost:3000
cd web
call npm run start
