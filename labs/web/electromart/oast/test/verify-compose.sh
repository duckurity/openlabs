#!/usr/bin/env bash
# Phase 3 OAST verification against the running Compose lab.
# Usage: bash oast/test/verify-compose.sh
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "== OAST container status =="
docker compose ps oast

echo "== OAST health on host loopback =="
docker compose exec -T oast node -e \
  "fetch('http://127.0.0.1:4000/health').then(async r=>{const j=await r.json();if(!r.ok||j.service!=='oast')process.exit(1);console.log(JSON.stringify(j))}).catch(e=>{console.error(e);process.exit(1)})"

echo "== Approved app container resolves attckerserver.local =="
docker compose exec -T app node -e \
  "fetch('http://attckerserver.local:4000/health').then(async r=>{const j=await r.json();if(!r.ok||j.service!=='oast')process.exit(1);console.log(j.service, j.status)}).catch(e=>{console.error(e);process.exit(1)})"

echo "== Bot container: callback reception and input limits =="
docker compose exec -T bot node - < oast/scripts/compose-check.js

echo "== Recent OAST interaction logs =="
docker compose logs --tail=30 oast

echo
echo "Dashboard: http://127.0.0.1:${OAST_HOST_PORT:-4000}/"
