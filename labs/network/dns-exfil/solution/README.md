# Solution: DNS Exfiltration

## Flag
FLAG{dns_3xf1ltr4t10n_1s_fun}

## Steps
1. Open dns_exfil.pcap in Wireshark or use tshark.
2. Filter DNS queries containing exfil.ctf.
3. Extract the query names, sort them (they have sequence numbers 01-, 02-, ...).
4. Strip the sequence prefix and the .exfil.ctf suffix.
5. Concatenate all chunks.
6. Base32-decode to get the flag.

## Command used
tshark -r dns_exfil.pcap -Y "dns.qry.name contains \"exfil.ctf\"" -T fields -e dns.qry.name | sort | sed 's/^[0-9]*-//' | sed 's/\.exfil\.ctf//' | tr -d '\n' | base32 -d

## Root Cause
DNS queries are sent in cleartext. An attacker can encode and exfiltrate data through subdomain labels. No DNS monitoring was in place to detect anomalous query patterns.

## Mitigation
- Monitor DNS for unusual query lengths, high volumes to a single domain, and non-standard character sets.
- Enforce egress DNS through approved resolvers only.
- Deploy DNS RPZ/filtering.
- Never rely on DNS for covert channels - encrypt sensitive data in transit.
