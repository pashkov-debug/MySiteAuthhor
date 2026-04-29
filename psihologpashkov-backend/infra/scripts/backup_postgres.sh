#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/psihologpashkov-${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

docker compose -f infra/compose.prod.yml exec -T postgres \
  pg_dump \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-psihologpashkov}" \
  -Fc \
  > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"