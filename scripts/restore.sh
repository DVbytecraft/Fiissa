#!/bin/bash
# restore.sh - Restore PostgreSQL from a backup file.
# Usage: ./scripts/restore.sh <path/to/backup.sql.gz>

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <path/to/backup.sql.gz>"
    echo "Available files:"
    ls -lh "$PROJECT_DIR/scripts/backup/"*.sql.gz 2>/dev/null || echo "(none)"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    log "ERROR: file $BACKUP_FILE not found"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    log "ERROR: $ENV_FILE not found"
    exit 1
fi

source "$ENV_FILE"

log "=== FIISSA RESTORE ==="
log "File: $BACKUP_FILE"
log ""
log "WARNING: this will DROP and RECREATE the current database."
read -r -p "Confirm (oui/non): " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    log "Restore cancelled."
    exit 0
fi

log "1/4 Stopping application services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop backend worker beat 2>/dev/null || true

log "2/4 Recreating database..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-fiissa}" -d postgres -c \
    "DROP DATABASE IF EXISTS ${POSTGRES_DB:-fiissa};"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-fiissa}" -d postgres -c \
    "CREATE DATABASE ${POSTGRES_DB:-fiissa};"

log "3/4 Restoring data..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}"
else
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}" < "$BACKUP_FILE"
fi

log "4/4 Restarting services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d backend worker beat

log "=== Restore completed ==="
log "Verify integrity with: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T backend curl -fsS http://localhost:8000/health"
