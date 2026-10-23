from scapy.all import *
import base64
import random

flag = "duck{dns_3xf1ltr4t10n_1s_fun}"

# Base32 encode
encoded = base64.b32encode(flag.encode()).decode().rstrip("=")

# Split into 4-char chunks
chunks = [encoded[i:i+4] for i in range(0, len(encoded), 4)]

packets = []

# Flag queries with sequence prefix: "01-RkxB.exfil.ctf"
for i, chunk in enumerate(chunks, start=1):
    query_name = f"{i:02d}-{chunk}.exfil.ctf"
    pkt = IP(dst="8.8.8.8")/UDP(sport=54321, dport=53)/DNS(rd=1, qd=DNSQR(qname=query_name))
    packets.append(pkt)

# Background noise
noise = [
    "google.com", "www.cloudflare.com", "github.com",
    "api.github.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
    "amazonaws.com", "kali.org", "debian.org"
]
for n in noise:
    for _ in range(3):
        packets.append(
            IP(dst="8.8.8.8")/UDP(sport=54321, dport=53)/DNS(rd=1, qd=DNSQR(qname=n))
        )

random.shuffle(packets)

wrpcap("dns_exfil.pcap", packets)
print(f"[+] Generated dns_exfil.pcap with {len(packets)} DNS queries ({len(chunks)} flag chunks + noise).")
