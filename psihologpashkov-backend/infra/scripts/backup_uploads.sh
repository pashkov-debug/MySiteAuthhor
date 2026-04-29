#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

BACKUP_DIR="${BACKUP_DIR:-./backups/uploads}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/uploads-${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

docker run --rm \
  -v psihologpashkov-backend_psihologpashkov_uploads_prod_data:/uploads:ro \
  -v "$(pwd)/${BACKUP_DIR}:/backup" \
  alpine \
  tar -czf "/backup/$(basename "${BACKUP_FILE}")" -C /uploads .

echo "Uploads backup created: ${BACKUP_FILE}"