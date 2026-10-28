#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

command -v docker >/dev/null || { echo "Docker CLI not found." >&2; exit 1; }
docker compose version >/dev/null

echo '[1/7] Build and start the lab'
docker compose up -d --build

wait_healthy() {
  local name="$1" status i
  for i in $(seq 1 60); do
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || true)"
    if [[ "$status" == "healthy" ]]; then return 0; fi
    if [[ "$status" == "unhealthy" ]]; then
      docker logs "$name" >&2 || true
      echo "Container $name is unhealthy." >&2
      return 1
    fi
    sleep 2
  done
  docker logs "$name" >&2 || true
  echo "Timed out waiting for $name (last status: ${status:-unknown})." >&2
  return 1
}

echo '[2/7] Wait for router and services'
for name in hardv2-router hardv2-jump01 hardv2-app01 hardv2-db01; do wait_healthy "$name"; done

echo '[3/7] Check Nmap and Edge services'
docker compose exec -T attacker nmap --version >/dev/null
docker compose exec -T attacker nmap -sT -Pn -p 21,22 jump01 -oG - | tee /tmp/hardv2-edge-scan.txt
grep -q '21/open/tcp' /tmp/hardv2-edge-scan.txt
grep -q '22/open/tcp' /tmp/hardv2-edge-scan.txt

echo '[4/7] Check direct routed access is filtered'
docker compose exec -T attacker nmap -sT -Pn -p 22,8080 172.28.20.20 -oG - | tee /tmp/hardv2-corp-scan.txt
grep -q '/filtered/' /tmp/hardv2-corp-scan.txt

echo '[5/7] Check app-to-data connectivity and flag'
docker compose exec -T app01 pg_isready -h db01 -p 5432 -U inventory_app
test "$(docker compose exec -T db01 cat /root/flag.txt | tr -d '\r\n')" = 'duck{Root_Access}'

echo '[6/7] Check firewall forwarding policy'
docker compose exec -T router iptables -S FORWARD | grep -q -- '-P FORWARD DROP'

echo '[7/7] Verify reset returns the target to a clean state'
docker compose down --remove-orphans
docker compose up -d
for name in hardv2-router hardv2-jump01 hardv2-app01 hardv2-db01; do wait_healthy "$name"; done
test "$(docker compose exec -T db01 cat /root/flag.txt | tr -d '\r\n')" = 'duck{Root_Access}'
if docker compose exec -T db01 grep -Fq '/bin/bash -p -i' /opt/dbops/rotate.sh; then
  echo 'Reset did not restore the maintenance script.' >&2
  exit 1
fi

echo 'Smoke test passed. This checks startup, intended Edge exposure, filtered routed access, app-to-DB reachability, firewall policy, flag contents, and clean container recreation.'
