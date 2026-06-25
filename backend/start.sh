#!/bin/bash
set -e

echo "[start.sh] Lancement Celery worker en arrière-plan..."
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &

CELERY_PID=$!
echo "[start.sh] Celery PID=$CELERY_PID"

echo "[start.sh] Lancement Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
