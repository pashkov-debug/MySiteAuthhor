#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found. Copy .env.prod.example to .env.prod and fill secrets." >&2
  exit 1
fi

docker compose -f infra/compose.prod.yml up -d --build
docker compose -f infra/compose.prod.yml exec api alembic upgrade head
docker compose -f infra/compose.prod.yml ps