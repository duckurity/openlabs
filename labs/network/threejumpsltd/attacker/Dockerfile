FROM kalilinux/kali-rolling
ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/kali.sources ]; then \
      sed -i \
        -e 's|https://http.kali.org/kali|http://kali.download/kali|g' \
        -e 's|http://http.kali.org/kali|http://kali.download/kali|g' \
        /etc/apt/sources.list.d/kali.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i \
        -e 's|https://http.kali.org/kali|http://kali.download/kali|g' \
        -e 's|http://http.kali.org/kali|http://kali.download/kali|g' \
        /etc/apt/sources.list; \
    fi; \
    rm -rf /var/lib/apt/lists/*; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates curl dnsutils iproute2 iputils-ping john libcap2-bin \
      netcat-openbsd nmap openssh-client postgresql-client tar gzip; \
    if [ -x /usr/lib/nmap/nmap ]; then \
      setcap -r /usr/lib/nmap/nmap || true; \
      setcap cap_net_raw+ep /usr/lib/nmap/nmap || true; \
    fi; \
    rm -rf /var/lib/apt/lists/*

COPY attacker-entrypoint.sh /usr/local/bin/attacker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/attacker-entrypoint.sh
CMD ["sleep", "infinity"]
