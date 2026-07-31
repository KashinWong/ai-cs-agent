#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[entrypoint] applying database migrations..."
alembic -c backend/alembic.ini upgrade head

echo "[entrypoint] seeding default tenant / agent / channels / bilingual FAQ..."
python scripts/seed.py

echo "[entrypoint] starting API (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
