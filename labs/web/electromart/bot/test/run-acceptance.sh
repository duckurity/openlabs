#!/usr/bin/env bash
# Run the review-comment acceptance suite against the real Compose app.
#
# The suite registers a temporary review author and posts harmless marker
# reviews. This wrapper pauses the persistent bot, starts from a freshly reset
# app, runs the Playwright tests, then restarts the app (clearing the temporary
# accounts/reviews) and brings the persistent bot back.
set -u

cd "$(dirname "$0")/../.." || exit 1

docker compose stop bot >/dev/null 2>&1 || true
docker compose restart app >/dev/null 2>&1 || true

# Wait for the health endpoint inside the app container.
for _ in $(seq 1 60); do
  if docker compose exec -T app node -e \
    "fetch('http://127.0.0.1:3000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" \
    >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose run --rm --no-deps \
  -v "$PWD/bot/src:/app/src:ro" \
  -v "$PWD/bot/test:/app/test:ro" \
  -e BOT_ACCEPTANCE_TIMEOUT_MS="${BOT_ACCEPTANCE_TIMEOUT_MS:-20000}" \
  bot node --test test/acceptance.test.js
status=$?

# Always restore a clean lab and the persistent service, even after a failure.
docker compose restart app >/dev/null 2>&1 || true
docker compose up -d bot >/dev/null 2>&1 || true
exit "$status"
