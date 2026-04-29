#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000/api/v1}"

TMP_DIR="$(mktemp -d)"
COOKIE_JAR="${TMP_DIR}/cookies.txt"
RESPONSE_FILE="${TMP_DIR}/response.json"
AVATAR_FILE="${TMP_DIR}/avatar.png"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

log() {
  printf "\n[smoke] %s\n" "$1"
}

fail() {
  printf "\n[smoke][fail] %s\n" "$1" >&2
  if [[ -f "${RESPONSE_FILE}" ]]; then
    printf "[smoke][response]\n" >&2
    cat "${RESPONSE_FILE}" >&2 || true
    printf "\n" >&2
  fi
  exit 1
}

expect_status() {
  local actual="$1"
  local expected="$2"
  local step="$3"

  if [[ "${actual}" != "${expected}" ]]; then
    fail "${step}: expected HTTP ${expected}, got HTTP ${actual}"
  fi
}

json_get() {
  local key="$1"

  python - "$RESPONSE_FILE" "$key" <<'PY'
import json
import sys

path = sys.argv[1]
key = sys.argv[2]

with open(path, "r", encoding="utf-8") as file:
    data = json.load(file)

value = data
for part in key.split("."):
    value = value[part]

print(value)
PY
}

EMAIL="smoke-$(date +%s)@example.com"
PASSWORD="old-password-123"
NEW_PASSWORD="new-password-123"

log "API base: ${API_BASE_URL}"

log "health check"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    "${API_BASE_URL}/healthz"
)"
expect_status "${STATUS}" "200" "health check"

log "register user ${EMAIL}"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X POST "${API_BASE_URL}/auth/register" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    --data "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"full_name\":\"Smoke User\"}"
)"
expect_status "${STATUS}" "201" "register"

log "login"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X POST "${API_BASE_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -c "${COOKIE_JAR}" \
    -b "${COOKIE_JAR}" \
    --data "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
expect_status "${STATUS}" "200" "login"

ACCESS_TOKEN="$(json_get "access_token")"
REFRESH_TOKEN="$(json_get "refresh_token")"

if [[ -z "${ACCESS_TOKEN}" || -z "${REFRESH_TOKEN}" ]]; then
  fail "login did not return tokens"
fi

log "refresh via HttpOnly cookie"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X POST "${API_BASE_URL}/auth/refresh" \
    -H "Accept: application/json" \
    -c "${COOKIE_JAR}" \
    -b "${COOKIE_JAR}"
)"
expect_status "${STATUS}" "200" "refresh"

ACCESS_TOKEN="$(json_get "access_token")"

log "read /me"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X GET "${API_BASE_URL}/me" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}"
)"
expect_status "${STATUS}" "200" "read me"

log "update profile"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X PATCH "${API_BASE_URL}/me" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    --data "{\"full_name\":\"Smoke User Updated\"}"
)"
expect_status "${STATUS}" "200" "update profile"

log "upload avatar"
printf "avatar-content" > "${AVATAR_FILE}"

STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X PATCH "${API_BASE_URL}/me/avatar" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -F "file=@${AVATAR_FILE};filename=avatar.png;type=image/png"
)"
expect_status "${STATUS}" "200" "upload avatar"

AVATAR_PATH="$(json_get "avatar_path")"

if [[ -z "${AVATAR_PATH}" || "${AVATAR_PATH}" == "None" ]]; then
  fail "avatar_path was not returned"
fi

log "delete avatar"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X DELETE "${API_BASE_URL}/me/avatar" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}"
)"
expect_status "${STATUS}" "200" "delete avatar"

log "change password"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X PATCH "${API_BASE_URL}/me/password" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    --data "{\"current_password\":\"${PASSWORD}\",\"new_password\":\"${NEW_PASSWORD}\"}"
)"
expect_status "${STATUS}" "200" "change password"

log "logout"
STATUS="$(
  curl -sS \
    -o "${RESPONSE_FILE}" \
    -w "%{http_code}" \
    -X POST "${API_BASE_URL}/auth/logout" \
    -H "Accept: application/json" \
    -c "${COOKIE_JAR}" \
    -b "${COOKIE_JAR}"
)"
expect_status "${STATUS}" "200" "logout"

log "OK: full local API smoke passed"