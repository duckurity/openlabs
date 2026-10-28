#!/bin/sh
set -eu

# These routes intentionally send direct probes toward the router/firewall,
# where cross-zone forwarding is blocked. Players should pivot through hosts.
ip route replace 172.28.20.0/24 via 172.28.10.254 dev eth0
ip route replace 172.28.30.0/24 via 172.28.10.254 dev eth0

exec "$@"
