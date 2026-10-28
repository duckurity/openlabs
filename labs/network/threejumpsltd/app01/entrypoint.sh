#!/bin/bash
set -euo pipefail
install -d -m 0755 /run/sshd
ssh-keygen -A
/usr/sbin/sshd -D -e &
SSHD_PID=$!
python3 -m http.server 8080 --bind 0.0.0.0 --directory /srv/www &
HTTP_PID=$!
trap 'kill "$SSHD_PID" "$HTTP_PID" 2>/dev/null || true' TERM INT
wait -n "$SSHD_PID" "$HTTP_PID"
