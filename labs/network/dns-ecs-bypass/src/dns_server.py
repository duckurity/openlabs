# src/dns_server.py
# CTF DNS server (Medium) – ECS-based access control + CNAME chain + base64 flag
import socket, struct, base64

FLAG_PLAIN = "duck{3cs_byp4ss_cn4m3_ch41n_b4s364}"
FLAG_B64   = base64.b64encode(FLAG_PLAIN.encode()).decode()

INTERNAL_PREFIX = "10.10.10."
LISTEN_PORT = 5353

ZONE = {
    "flag.ctf.local":            ("CNAME", "secret.internal.ctf.local"),
    "secret.internal.ctf.local": ("TXT",   FLAG_B64),
}

def parse_qname(data, idx):
    labels = []
    while data[idx] != 0:
        ln = data[idx]; idx += 1
        labels.append(data[idx:idx+ln].decode(errors="ignore")); idx += ln
    idx += 1
    return ".".join(labels), idx

def parse_question(data):
    qname, idx = parse_qname(data, 12)
    qtype, qclass = struct.unpack("!HH", data[idx:idx+4])
    return qname, qtype, idx + 4

def parse_ecs(data, start):
    idx = start
    try:
        while idx + 11 <= len(data):
            if data[idx] & 0xC0 == 0xC0:
                idx += 2
            else:
                while data[idx] != 0:
                    idx += data[idx] + 1
                idx += 1
            if idx + 10 > len(data):
                break
            rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", data[idx:idx+10])
            idx += 10
            rdata = data[idx:idx+rdlen]
            if rtype == 41:
                o = 0
                while o + 4 <= len(rdata):
                    code, olen = struct.unpack("!HH", rdata[o:o+4]); o += 4
                    opt = rdata[o:o+olen]; o += olen
                    if code == 8 and olen >= 4:
                        family, src_prefix, scope = struct.unpack("!HBB", opt[:4])
                        addr = opt[4:]
                        ip = socket.inet_ntoa(addr + b"\x00"*(4-len(addr)))
                        return ip
            idx += rdlen
    except Exception:
        pass
    return None

def encode_name(name):
    out = b""
    for part in name.split("."):
        out += bytes([len(part)]) + part.encode()
    return out + b"\x00"

def build_answer(qname, ip_ok):
    if not ip_ok:
        return b"", 0, 5
    if qname not in ZONE:
        return b"", 0, 3
    rtype, value = ZONE[qname]
    qname_wire = encode_name(qname)
    if rtype == "CNAME":
        rdata = encode_name(value)
        rr = qname_wire + struct.pack("!HHIH", 5, 1, 60, len(rdata)) + rdata
        return rr, 1, 0
    if rtype == "TXT":
        txt = value.encode()
        rdata = bytes([len(txt)]) + txt
        rr = qname_wire + struct.pack("!HHIH", 16, 1, 60, len(rdata)) + rdata
        return rr, 1, 0
    return b"", 0, 3

def build_response(query, ip_ok):
    tid = query[:2]
    qname, qtype, qend = parse_question(query)
    question = query[12:qend]
    answer, ancount, rcode = build_answer(qname, ip_ok)
    flags = 0x8180 | rcode
    header = tid + struct.pack("!HHHHH", flags, 1, ancount, 0, 0)
    return header + question + answer

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", LISTEN_PORT))
    print(f"[*] DNS CTF server listening on udp/{LISTEN_PORT}")
    while True:
        data, addr = s.recvfrom(1024)
        try:
            qname, qtype, qend = parse_question(data)
            ecs_ip = parse_ecs(data, qend)
            ip_ok = ecs_ip is not None and ecs_ip.startswith(INTERNAL_PREFIX)
            print(f"[+] {addr} q={qname} ecs={ecs_ip} ok={ip_ok}")
            s.sendto(build_response(data, ip_ok), addr)
        except Exception as e:
            print("[!]", e)

if __name__ == "__main__":
    main()
