#!/bin/bash
# Solve script for DNS Exfiltration challenge
PCAP="$1"
if [ -z "$PCAP" ]; then
    echo "Usage: $0 <pcap_file>"
    exit 1
fi
tshark -r "$PCAP" -Y "dns.qry.name contains \"exfil.ctf\"" -T fields -e dns.qry.name \
  | sort \
  | sed 's/^[0-9]*-//' \
  | sed 's/\.exfil\.ctf//' \
  | tr -d '\n' \
  | base32 -d
