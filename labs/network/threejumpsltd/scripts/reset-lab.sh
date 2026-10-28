#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down --remove-orphans
docker compose up -d
printf '\nContainers recreated. Check readiness with: docker compose ps\n'
