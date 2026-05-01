#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found." >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/opt/psihologpashkov-backups/uploads}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/uploads-${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

docker compose --env-file .env.prod -f infra/compose.prod.yml exec -T api \
  python -c 'import pathlib, sys, tarfile; root = pathlib.Path("/app/backend/uploads"); archive = tarfile.open(fileobj=sys.stdout.buffer, mode="w:gz"); archive.add(root, arcname="."); archive.close()' \
  > "${BACKUP_FILE}"

echo "Uploads backup created: ${BACKUP_FILE}"