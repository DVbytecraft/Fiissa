#!/bin/bash
# restore.sh — Restauration depuis une sauvegarde PostgreSQL
# Usage : ./scripts/restore.sh <chemin/vers/backup.sql.gz>
# DANGER : Écrase la base de données actuelle.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ -z "${1:-}" ]; then
    echo "Usage : $0 <chemin/vers/backup.sql.gz>"
    echo "Fichiers disponibles :"
    ls -lh "$PROJECT_DIR/scripts/backup/"*.sql.gz 2>/dev/null || echo "(aucun)"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    log "ERREUR : Fichier $BACKUP_FILE introuvable"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    log "ERREUR : $ENV_FILE introuvable"
    exit 1
fi

source "$ENV_FILE"

log "=== RESTAURATION FIISSA ==="
log "Fichier : $BACKUP_FILE"
log ""
log "ATTENTION : Cette opération va SUPPRIMER et RECRÉER la base de données."
read -r -p "Confirmer (oui/non) : " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    log "Restauration annulée."
    exit 0
fi

# Arrêter l'application (pas la DB)
log "1/4 Arrêt des services application..."
docker compose -f "$COMPOSE_FILE" stop backend worker beat 2>/dev/null || true

# Drop + recreate DB
log "2/4 Réinitialisation base de données..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-fiissa}" -c \
    "DROP DATABASE IF EXISTS ${POSTGRES_DB:-fiissa}; CREATE DATABASE ${POSTGRES_DB:-fiissa};"

# Restore
log "3/4 Restauration données..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}"
else
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-fiissa}" "${POSTGRES_DB:-fiissa}" < "$BACKUP_FILE"
fi

log "4/4 Redémarrage services..."
docker compose -f "$COMPOSE_FILE" up -d backend worker beat

log "=== Restauration terminée ==="
log "Pensez à vérifier l'intégrité : curl http://localhost:8000/health"
