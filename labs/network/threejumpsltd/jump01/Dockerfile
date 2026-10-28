FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server vsftpd iproute2 ca-certificates sudo nmap libcap2-bin \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system ops \
    && useradd --create-home --user-group --shell /bin/bash --groups ops labuser \
    && echo 'labuser:Harbor2026!' | chpasswd \
    && if [ -x /usr/lib/nmap/nmap ]; then setcap -r /usr/lib/nmap/nmap || true; setcap cap_net_raw+ep /usr/lib/nmap/nmap; fi \
    && install -d -m 0755 /run/sshd /srv/ftp /srv/ftp/pub/archive

COPY 99-lab.conf /etc/ssh/sshd_config.d/99-lab.conf
COPY vsftpd.conf /etc/vsftpd.conf
COPY entrypoint.sh /usr/local/sbin/jump-entrypoint.sh
COPY ftp-src/ /srv/ftp/
COPY archive-src/ /tmp/archive-src/

RUN set -eux; \
    tar -czf /srv/ftp/pub/archive/ops-backup.tar.gz -C /tmp/archive-src .; \
    rm -rf /tmp/archive-src; \
    chown -R root:root /srv/ftp; \
    find /srv/ftp -type d -exec chmod 0755 {} \;; \
    find /srv/ftp -type f -exec chmod 0644 {} \;; \
    chmod 0755 /usr/local/sbin/jump-entrypoint.sh; \
    chmod 0644 /etc/ssh/sshd_config.d/99-lab.conf /etc/vsftpd.conf

EXPOSE 21 22 21100-21110
ENTRYPOINT ["/usr/local/sbin/jump-entrypoint.sh"]

RUN install -d -o root -g root -m 0555 /var/run/vsftpd/empty
