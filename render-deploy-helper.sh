#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  echo "[render-helper] Creating virtualenv (.venv)"
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip

REQ_FILE="requirements.txt"
if [[ ! -f "$REQ_FILE" ]] && [[ -f server/requirements.txt ]]; then
  REQ_FILE="server/requirements.txt"
fi

echo "[render-helper] Installing dependencies from $REQ_FILE"
pip install -r "$REQ_FILE"

if [[ -f alembic.ini ]]; then
  echo "[render-helper] Running Alembic migrations"
  alembic upgrade head || true
fi

echo "[render-helper] Starting gunicorn on http://127.0.0.1:8000"
exec gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

# Reminder for Render
# Start Command: gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app

