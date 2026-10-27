# DNS Exfiltration EASY · network

## Brief
A compromised host leaked data through DNS queries. The capture is in `app/dns_exfil.pcap`.

## Setup
Run `docker compose up -d` and open `http://localhost:8080/dns_exfil.pcap`.

## Goal
Analyze the capture and recover the exfiltrated flag. Verify your solve with `python3 scripts/check.py labs/network/dns-exfil`.
