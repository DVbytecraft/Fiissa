#!/bin/bash
# rollback.sh — Rollback manuel vers un commit Git précédent
# Usage : ./scripts/rollback.sh
# Ce script est le rollback MANUEL (le rollback automatique est dans deploy.sh via trap EXIT).

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { log "ERREUR : $*"; }

if [ ! -f "$ENV_FILE" ]; then
    error "$ENV_FILE introuvable."
    exit 1
fi

log "=== ROLLBACK MANUEL Fiissa $(date) ==="
log ""
log "Commits récents :"
git -C "$PROJECT_DIR" log --oneline -10
log ""

read -r -p "Hash du commit à restaurer (laisser vide pour annuler) : " COMMIT
if [ -z "$COMMIT" ]; then
    log "Rollback annulé."
    exit 0
fi

# Vérifier que le commit existe
if ! git -C "$PROJECT_DIR" cat-file -t "$COMMIT" &>/dev/null; then
    error "Commit '$COMMIT' introuvable."
    exit 1
fi

log "ATTENTION : Le code sera restauré au commit $COMMIT"
read -r -p "Confirmer (oui/non) : " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    log "Rollback annulé."
    exit 0
fi

# Sauvegarder l'état actuel
log "Sauvegarde de l'état actuel..."
git -C "$PROJECT_DIR" stash push -m "pre-rollback-$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

# Checkout du commit cible
log "Restauration vers le commit $COMMIT..."
git -C "$PROJECT_DIR" checkout "$COMMIT"

# Rebuild et redémarrage
log "Build des images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build backend frontend

log "Redémarrage des services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend worker beat frontend

# Health check post-rollback
log "Health check (60s max)..."
HEALTH_OK=false
for i in $(seq 1 12); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        log "API opérationnelle après rollback (tentative $i/12)"
        HEALTH_OK=true
        break
    fi
    log "   Attente... ($i/12)"
    sleep 5
done

if [ "$HEALTH_OK" = false ]; then
    error "API non disponible après rollback — intervention manuelle requise"
    log "Logs : docker compose -f $COMPOSE_FILE logs --tail=100 backend"
    exit 1
fi

log "=== Rollback vers $COMMIT terminé avec succès ==="
