#!/bin/bash
# deploy.sh — Déploiement Fiissa en production avec rollback automatique
# Usage : ./scripts/deploy.sh [--no-migrate] [--no-backup]
# Prérequis : docker, docker compose, .env.prod

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"
BACKUP_DIR="$PROJECT_DIR/scripts/backup"
LOG_FILE="$PROJECT_DIR/deploy.log"
ROLLBACK_MARKER="$PROJECT_DIR/.rollback_available"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
error(){ log "ERREUR : $*"; }
ok()   { log "✓ $*"; }

# ── Nettoyage en cas d'échec ───────────────────────────────────────────────────
_rollback() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log ""
        log "════════════════════════════════════════"
        log "⚠  DÉPLOIEMENT ÉCHOUÉ (exit $exit_code) — ROLLBACK AUTOMATIQUE"
        log "════════════════════════════════════════"

        if [ -f "$ROLLBACK_MARKER" ]; then
            local prev_image
            prev_image=$(cat "$ROLLBACK_MARKER")
            log "Image précédente : $prev_image"

            log "Rollback : restauration de l'image précédente..."
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
                down --remove-orphans 2>/dev/null || true

            # Retag l'ancienne image et redémarrer
            docker tag "$prev_image" "fiissa_backend:latest" 2>/dev/null || true
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
                up -d --no-deps backend worker beat 2>/dev/null || true

            # Health check post-rollback
            local retries=0
            while [ $retries -lt 6 ]; do
                if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
                    ok "Rollback réussi — API opérationnelle"
                    rm -f "$ROLLBACK_MARKER"
                    break
                fi
                retries=$((retries + 1))
                sleep 5
            done

            if [ $retries -eq 6 ]; then
                error "Rollback échoué — intervention manuelle requise"
                log "Commandes de récupération :"
                log "  docker compose -f $COMPOSE_FILE logs --tail=100 backend"
                log "  docker compose -f $COMPOSE_FILE restart backend"
            fi
        else
            log "Pas d'image précédente disponible — premier déploiement ?"
            log "Vérifiez manuellement : docker compose -f $COMPOSE_FILE logs backend"
        fi
    fi
}

trap _rollback EXIT

log "════════════════════════════════════════"
log "=== Déploiement Fiissa ==="
log "Git : $(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'non-git')"
log "════════════════════════════════════════"

# ── Vérifications préalables ───────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    error "$ENV_FILE introuvable. Copier .env.prod.example vers .env.prod."
    exit 1
fi

if ! command -v docker &>/dev/null; then
    error "Docker non installé."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# ── Sauvegarder l'image actuelle pour rollback ────────────────────────────────
CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' \
    "$(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q backend 2>/dev/null)" \
    2>/dev/null || echo "")

if [ -n "$CURRENT_IMAGE" ]; then
    SNAPSHOT_TAG="fiissa_backend:rollback_$(date +%Y%m%d_%H%M%S)"
    docker tag "$CURRENT_IMAGE" "$SNAPSHOT_TAG" 2>/dev/null && \
        echo "$SNAPSHOT_TAG" > "$ROLLBACK_MARKER" && \
        log "Image rollback sauvegardée : $SNAPSHOT_TAG"
fi

# ── 1. Sauvegarde DB pré-déploiement ─────────────────────────────────────────
if [[ "${2:-}" != "--no-backup" ]]; then
    log "1/7 Sauvegarde pré-déploiement..."
    BACKUP_FILE="$BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps postgres | grep -q "running"; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
            pg_dump -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}" \
            | gzip > "$BACKUP_FILE" && \
            ok "Backup créé : $(basename "$BACKUP_FILE") ($(du -sh "$BACKUP_FILE" | cut -f1))"
    else
        log "1/7 DB pas encore démarrée — backup ignoré (premier déploiement ?)"
    fi
else
    log "1/7 Backup ignoré (--no-backup)"
fi

# ── 2. Pull nouvelles images ──────────────────────────────────────────────────
log "2/7 Pull images Docker..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
ok "Images à jour"

# ── 3. Migrations Alembic ─────────────────────────────────────────────────────
if [[ "${1:-}" != "--no-migrate" ]]; then
    log "3/7 Migrations Alembic..."

    # Vérifier d'abord que les migrations peuvent s'appliquer (dry-run via check)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm \
        -e DATABASE_URL \
        backend alembic check 2>/dev/null && log "Migrations : déjà à jour" || {
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm \
            -e DATABASE_URL \
            backend alembic upgrade head
        ok "Migrations appliquées"
    }
else
    log "3/7 Migrations ignorées (--no-migrate)"
fi

# ── 4. Seed superadmin ────────────────────────────────────────────────────────
log "4/7 Seed superadmin (si absent)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm \
    backend python scripts/seed.py 2>/dev/null && ok "Seed OK" || log "⚠ Seed ignoré (déjà fait ou erreur)"

# ── 5. Redémarrage des services ───────────────────────────────────────────────
log "5/7 Redémarrage services (blue-green rolling)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    --no-deps --remove-orphans \
    backend worker beat
ok "Services redémarrés"

# ── 6. Health check ───────────────────────────────────────────────────────────
log "6/7 Health check (60s max)..."
HEALTH_OK=false
for i in $(seq 1 12); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        ok "API opérationnelle (tentative $i/12)"
        HEALTH_OK=true
        break
    fi
    log "   Attente... ($i/12)"
    sleep 5
done

if [ "$HEALTH_OK" = false ]; then
    error "API non disponible après 60s"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50 backend
    exit 1  # déclenche le trap → rollback automatique
fi

# ── 7. Nettoyage ──────────────────────────────────────────────────────────────
log "7/7 Nettoyage images inutilisées..."
docker image prune -f >/dev/null 2>&1 || true

# Tout s'est bien passé : supprimer le marqueur rollback
rm -f "$ROLLBACK_MARKER"
ok "Marqueur rollback supprimé (déploiement confirmé)"

log ""
log "════════════════════════════════════════"
log "=== Déploiement terminé avec succès ==="
log "Git : $(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
log "════════════════════════════════════════"

# Désactiver le trap (succès)
trap - EXIT
