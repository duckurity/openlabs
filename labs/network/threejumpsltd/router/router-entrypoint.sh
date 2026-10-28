#!/bin/sh
set -eu

EDGE_IF="$(ip -o -4 addr show | awk '$4 ~ /^172\.28\.10\.254\// {print $2; exit}')"
CORP_IF="$(ip -o -4 addr show | awk '$4 ~ /^172\.28\.20\.254\// {print $2; exit}')"
DATA_IF="$(ip -o -4 addr show | awk '$4 ~ /^172\.28\.30\.254\// {print $2; exit}')"

if [ -z "$EDGE_IF" ] || [ -z "$CORP_IF" ] || [ -z "$DATA_IF" ]; then
  echo "Could not identify all three router interfaces." >&2
  ip -br address >&2
  exit 1
fi

# Compose sets net.ipv4.ip_forward=1. Keep the firewall policy restrictive.
iptables -w -F FORWARD
iptables -w -P FORWARD DROP
iptables -w -A FORWARD -m conntrack --ctstate INVALID -j DROP
iptables -w -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Direct routed access between zones is intentionally blocked. Access to the
# next zone must be made through the dual-homed jump01/app01 hosts.
iptables -w -A FORWARD -i "$EDGE_IF" -o "$CORP_IF" -j DROP
iptables -w -A FORWARD -i "$EDGE_IF" -o "$DATA_IF" -j DROP
iptables -w -A FORWARD -i "$CORP_IF" -o "$EDGE_IF" -j DROP
iptables -w -A FORWARD -i "$CORP_IF" -o "$DATA_IF" -j DROP
iptables -w -A FORWARD -i "$DATA_IF" -o "$EDGE_IF" -j DROP
iptables -w -A FORWARD -i "$DATA_IF" -o "$CORP_IF" -j DROP

iptables -w -P INPUT ACCEPT
iptables -w -P OUTPUT ACCEPT

echo "Router/firewall ready: edge=$EDGE_IF corporate=$CORP_IF data=$DATA_IF"
echo "Forwarding is enabled; inter-zone routed flows default to DROP."
exec tail -f /dev/null
