#!/bin/bash
# Sauvegarde quotidienne PostgreSQL — à planifier via cron
# Cron: 0 2 * * * /app/scripts/backup.sh

set -euo pipefail

BACKUP_DIR="/backup"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="fiissa_backup_${DATE}.sql.gz"
KEEP_DAYS=30

source /app/.env.prod 2>/dev/null || true

echo "[$(date)] Début sauvegarde SmartCheckout..."

pg_dump \
  -h "${POSTGRES_HOST:-postgres}" \
  -U "${POSTGRES_USER:-fiissa}" \
  -d "${POSTGRES_DB:-fiissa}" \
  --no-password \
  | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "[$(date)] Sauvegarde créée : ${FILENAME} ($(du -sh ${BACKUP_DIR}/${FILENAME} | cut -f1))"

# Supprimer les sauvegardes plus vieilles que KEEP_DAYS jours
find "${BACKUP_DIR}" -name "fiissa_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] Nettoyage : fichiers > ${KEEP_DAYS} jours supprimés"

echo "[$(date)] Sauvegarde terminée."
