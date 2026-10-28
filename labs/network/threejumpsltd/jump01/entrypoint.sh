#!/bin/bash
set -euo pipefail
install -d -m 0755 /run/sshd
ssh-keygen -A
/usr/sbin/sshd -D -e &
SSHD_PID=$!
/usr/sbin/vsftpd /etc/vsftpd.conf &
FTP_PID=$!
trap 'kill "$SSHD_PID" "$FTP_PID" 2>/dev/null || true' TERM INT
wait -n "$SSHD_PID" "$FTP_PID"
