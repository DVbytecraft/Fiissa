#!/bin/bash
# No set -e: we keep the container alive even if alembic fails.
# Uvicorn must stay up so Render's health check keeps passing.

echo "[start.sh] Starting Uvicorn..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &
UVICORN_PID=$!
echo "[start.sh] Uvicorn PID=$UVICORN_PID"

echo "[start.sh] Waiting for Uvicorn (max 30s)..."
UVICORN_READY=0
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[start.sh] Uvicorn ready (attempt $i)"
    UVICORN_READY=1
    break
  fi
  sleep 2
done

if [ "$UVICORN_READY" = "0" ]; then
  echo "[start.sh] WARNING: Uvicorn not ready after 30s — proceeding anyway"
fi

echo "[start.sh] Running Alembic migrations..."
alembic upgrade head
ALEMBIC_EXIT=$?
if [ "$ALEMBIC_EXIT" = "0" ]; then
  echo "[start.sh] Migrations OK"
else
  echo "[start.sh] ERROR: Alembic exited with code $ALEMBIC_EXIT — keeping container alive"
fi

echo "[start.sh] Starting Celery worker..."
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &
CELERY_PID=$!
echo "[start.sh] Celery PID=$CELERY_PID"

echo "[start.sh] All processes started. Waiting on Uvicorn PID=$UVICORN_PID..."
wait $UVICORN_PID
UVICORN_EXIT=$?
echo "[start.sh] Uvicorn exited with code $UVICORN_EXIT"
exit $UVICORN_EXIT
