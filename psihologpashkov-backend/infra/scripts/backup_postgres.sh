#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found." >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/opt/psihologpashkov-backups/postgres}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/psihologpashkov-${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

docker compose --env-file .env.prod -f infra/compose.prod.yml exec -T postgres \
  sh -c 'pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-psihologpashkov}" -Fc' \
  > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"