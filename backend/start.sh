#!/bin/bash
set -e

echo "[start.sh] Starting Uvicorn (health check must pass quickly)..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &
UVICORN_PID=$!

echo "[start.sh] Waiting for Uvicorn to be ready..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[start.sh] Uvicorn ready after ${i}s"
    break
  fi
  sleep 2
done

echo "[start.sh] Running Alembic migrations..."
alembic upgrade head
echo "[start.sh] Migrations done."

echo "[start.sh] Starting Celery worker..."
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &

echo "[start.sh] All processes running. Waiting on Uvicorn (PID=$UVICORN_PID)..."
wait $UVICORN_PID
