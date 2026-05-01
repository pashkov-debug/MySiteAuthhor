#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

BACKUP_ROOT="${BACKUP_ROOT:-/opt/psihologpashkov-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "${BACKUP_ROOT}/postgres"
mkdir -p "${BACKUP_ROOT}/uploads"

echo "[backup] started at $(date -Is)"

BACKUP_DIR="${BACKUP_ROOT}/postgres" bash infra/scripts/backup_postgres.sh
BACKUP_DIR="${BACKUP_ROOT}/uploads" bash infra/scripts/backup_uploads.sh

find "${BACKUP_ROOT}/postgres" -type f -name "*.dump" -mtime "+${RETENTION_DAYS}" -delete
find "${BACKUP_ROOT}/uploads" -type f -name "*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "[backup] finished at $(date -Is)"