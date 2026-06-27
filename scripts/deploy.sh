#!/bin/bash
# deploy.sh - Production deployment with health validation and rollback.
# Usage: ./scripts/deploy.sh [--no-migrate] [--no-backup]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"
BACKUP_DIR="$PROJECT_DIR/scripts/backup"
LOG_FILE="$PROJECT_DIR/deploy.log"
ROLLBACK_MARKER="$PROJECT_DIR/.rollback_available"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
error() { log "ERROR: $*"; }
ok() { log "[ok] $*"; }
compose() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

health_status() {
    local service="$1"
    local container_id
    container_id="$(compose ps -q "$service" 2>/dev/null || true)"
    if [ -z "$container_id" ]; then
        echo "missing"
        return 1
    fi
    docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id"
}

rollback_on_failure() {
    local exit_code=$?
    if [ "$exit_code" -eq 0 ]; then
        return
    fi

    log ""
    log "========================================"
    log "DEPLOYMENT FAILED (exit $exit_code)"
    log "========================================"

    if [ -f "$ROLLBACK_MARKER" ]; then
        local previous_image
        previous_image="$(cat "$ROLLBACK_MARKER")"
        log "Previous image: $previous_image"

        compose down --remove-orphans 2>/dev/null || true
        docker tag "$previous_image" "fiissa_backend:latest" 2>/dev/null || true
        compose up -d --remove-orphans postgres redis minio backend worker beat frontend nginx 2>/dev/null || true

        local retries=0
        while [ "$retries" -lt 6 ]; do
            if compose exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
                ok "Automatic rollback succeeded"
                rm -f "$ROLLBACK_MARKER"
                break
            fi
            retries=$((retries + 1))
            sleep 5
        done

        if [ "$retries" -eq 6 ]; then
            error "Automatic rollback failed. Manual intervention required."
            log "Inspect with: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs --tail=100 backend"
        fi
    else
        log "No rollback image available. This may be the first deployment."
    fi
}

trap rollback_on_failure EXIT

log "========================================"
log "=== Fiissa Deployment ==="
log "Git: $(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'non-git')"
log "========================================"

if [ ! -f "$ENV_FILE" ]; then
    error "$ENV_FILE not found. Copy .env.prod.example to .env.prod first."
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    error "Docker is not installed."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    error "Docker Compose plugin is not available."
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"

CURRENT_IMAGE="$(docker inspect --format='{{.Config.Image}}' "$(compose ps -q backend 2>/dev/null)" 2>/dev/null || echo "")"
if [ -n "$CURRENT_IMAGE" ]; then
    SNAPSHOT_TAG="fiissa_backend:rollback_$(date +%Y%m%d_%H%M%S)"
    docker tag "$CURRENT_IMAGE" "$SNAPSHOT_TAG" 2>/dev/null || true
    echo "$SNAPSHOT_TAG" > "$ROLLBACK_MARKER"
    log "Rollback image saved: $SNAPSHOT_TAG"
fi

if [[ "${2:-}" != "--no-backup" ]]; then
    log "1/7 Pre-deploy database backup..."
    BACKUP_FILE="$BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
    if compose ps --status running postgres | grep -q postgres; then
        compose exec -T postgres pg_dump -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}" | gzip > "$BACKUP_FILE"
        ok "Backup created: $(basename "$BACKUP_FILE")"
    else
        log "Postgres is not running yet, backup skipped."
    fi
else
    log "1/7 Backup skipped (--no-backup)"
fi

log "2/7 Build Docker images..."
compose build --pull backend worker beat frontend
ok "Application images built"

log "3/7 Start base services..."
compose up -d --remove-orphans postgres redis minio
ok "Base services started"

if [[ "${1:-}" != "--no-migrate" ]]; then
    log "4/7 Run database migrations..."
    compose run --rm -e DATABASE_URL backend alembic check 2>/dev/null && log "Migrations already up to date" || {
        compose run --rm -e DATABASE_URL backend alembic upgrade head
        ok "Migrations applied"
    }
else
    log "4/7 Migrations skipped (--no-migrate)"
fi

log "5/7 Seed superadmin if needed..."
compose run --rm backend python scripts/seed.py 2>/dev/null && ok "Seed completed" || log "Seed skipped or already applied"

log "6/7 Start full application stack..."
compose up -d --remove-orphans backend worker beat frontend nginx certbot
ok "Application stack started"

log "7/7 Validate service health..."
HEALTH_OK=false
for i in $(seq 1 18); do
    if compose exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        HEALTH_OK=true
        ok "Backend health endpoint responded (attempt $i/18)"
        break
    fi
    log "Waiting for backend health... ($i/18)"
    sleep 5
done

if [ "$HEALTH_OK" = false ]; then
    error "Backend health endpoint did not become ready within 90s"
    compose logs --tail=50 backend
    exit 1
fi

for service in postgres redis minio backend worker beat frontend nginx; do
    SERVICE_HEALTH="$(health_status "$service" || true)"
    if [ "$SERVICE_HEALTH" != "healthy" ] && [ "$SERVICE_HEALTH" != "running" ]; then
        error "Service $service is not healthy: $SERVICE_HEALTH"
        compose ps
        exit 1
    fi
done

log "Cleanup unused Docker images..."
docker image prune -f >/dev/null 2>&1 || true

rm -f "$ROLLBACK_MARKER"
ok "Rollback marker removed"
log "=== Deployment completed successfully ==="

trap - EXIT
