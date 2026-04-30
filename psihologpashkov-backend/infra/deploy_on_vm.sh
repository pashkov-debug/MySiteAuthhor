#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found on VM." >&2
  exit 1
fi

if [[ ! -f "/opt/psihologpashkov-certs/fullchain.pem" ]]; then
  echo "ERROR: /opt/psihologpashkov-certs/fullchain.pem not found." >&2
  exit 1
fi

if [[ ! -f "/opt/psihologpashkov-certs/privkey.pem" ]]; then
  echo "ERROR: /opt/psihologpashkov-certs/privkey.pem not found." >&2
  exit 1
fi

docker compose --env-file .env.prod -f infra/compose.prod.yml up -d --no-build
docker compose --env-file .env.prod -f infra/compose.prod.yml exec -T api alembic upgrade head
docker compose --env-file .env.prod -f infra/compose.prod.yml ps