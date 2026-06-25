#!/bin/bash
set -e

echo "[start.sh] Running Alembic migrations..."
alembic upgrade head
echo "[start.sh] Migrations done."

echo "[start.sh] Starting Celery worker in background..."
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &

CELERY_PID=$!
echo "[start.sh] Celery PID=$CELERY_PID"

echo "[start.sh] Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
