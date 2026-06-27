#!/bin/bash
# rollback.sh - Manual rollback to a previous git commit.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { log "ERROR: $*"; }
compose() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

if [ ! -f "$ENV_FILE" ]; then
    error "$ENV_FILE not found."
    exit 1
fi

log "=== FIISSA MANUAL ROLLBACK $(date) ==="
log ""
log "Recent commits:"
git -C "$PROJECT_DIR" log --oneline -10
log ""

read -r -p "Commit hash to restore (empty to cancel): " COMMIT
if [ -z "$COMMIT" ]; then
    log "Rollback cancelled."
    exit 0
fi

if ! git -C "$PROJECT_DIR" cat-file -t "$COMMIT" >/dev/null 2>&1; then
    error "Commit '$COMMIT' not found."
    exit 1
fi

log "WARNING: source code will be restored to commit $COMMIT"
read -r -p "Confirm (oui/non): " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    log "Rollback cancelled."
    exit 0
fi

log "Saving current state..."
git -C "$PROJECT_DIR" stash push -m "pre-rollback-$(date +%Y%m%d_%H%M%S)" >/dev/null 2>&1 || true

log "Checking out commit $COMMIT..."
git -C "$PROJECT_DIR" checkout "$COMMIT"

log "Building images..."
compose build --pull backend worker beat frontend

log "Restarting services..."
compose up -d --remove-orphans backend worker beat frontend nginx

log "Health check (60s max)..."
HEALTH_OK=false
for i in $(seq 1 12); do
    if compose exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        log "API healthy after rollback (attempt $i/12)"
        HEALTH_OK=true
        break
    fi
    log "Waiting... ($i/12)"
    sleep 5
done

if [ "$HEALTH_OK" = false ]; then
    error "API still unavailable after rollback. Manual intervention required."
    log "Logs: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs --tail=100 backend"
    exit 1
fi

log "=== Rollback to $COMMIT completed successfully ==="
