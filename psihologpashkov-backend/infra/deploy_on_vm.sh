#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found on VM." >&2
  echo "Create it from .env.prod.example and fill real secrets." >&2
  exit 1
fi

echo "[deploy] building and starting production stack"
docker compose -f infra/compose.prod.yml up -d --build

echo "[deploy] applying migrations"
docker compose -f infra/compose.prod.yml exec -T api alembic upgrade head

echo "[deploy] checking containers"
docker compose -f infra/compose.prod.yml ps

echo "[deploy] waiting for API health"
for i in {1..30}; do
  if docker compose -f infra/compose.prod.yml exec -T api curl -fsS http://127.0.0.1:8000/api/v1/healthz >/dev/null; then
    echo "[deploy] API health OK"
    exit 0
  fi

  echo "[deploy] API not ready yet, retry ${i}/30"
  sleep 2
done

echo "[deploy] API health check failed" >&2
docker compose -f infra/compose.prod.yml logs --tail=100 api
exit 1