# DNS Exfiltration Challenge

**Category:** Network Forensics
**Difficulty:** Easy

## Description
We captured traffic from a compromised host on our network. The attacker appears to be leaking data via DNS queries. Analyze the provided packet capture (`dns_exfil.pcap`) and recover the exfiltrated flag.

**Flag Format:** `duck{...}`

## Hints
1. Look at the DNS queries in the capture.
2. Some queries stand out from normal browsing traffic.
3. The subdomain labels are encoded. The order of the queries is important.

## Verification
You can verify your flag using the platform's checker:
`python3 ../../../scripts/check.py .`
