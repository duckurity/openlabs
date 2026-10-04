#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BASE_URL=${BASE_URL:-http://127.0.0.1:${CHALLENGE_PORT:-4000}}
export BASE_URL

command -v curl >/dev/null 2>&1 || {
  echo "FAIL: curl is required" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "FAIL: python3 is required" >&2
  exit 1
}

curl -fsS "$BASE_URL/" >/dev/null
curl -fsS "$BASE_URL/login" >/dev/null
curl -fsS "$BASE_URL/register" >/dev/null

inbox_status=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL/inbox")
if [ "$inbox_status" != "403" ]; then
  echo "FAIL: unauthenticated /inbox returned HTTP $inbox_status" >&2
  exit 1
fi

python3 "$ROOT_DIR/tools/validate_challenge.py"

if [ "${SKIP_ELIXIR_TESTS:-0}" != "1" ]; then
  docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T app sh -lc 'MIX_ENV=test mix test'
fi

echo "PASS: challenge validation completed"
