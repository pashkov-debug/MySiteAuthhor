#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "ERROR: API_BASE_URL is required, example:" >&2
  echo "API_BASE_URL=https://api.psihologpashkov.ru/api/v1 ./infra/scripts/smoke_api_prod.sh" >&2
  exit 1
fi

./infra/scripts/smoke_api_local.sh