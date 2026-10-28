FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server python3 iproute2 iputils-ping netcat-openbsd dnsutils curl postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --user-group --shell /bin/bash appsvc \
    && echo 'appsvc:AppDeploy2026!' | chpasswd \
    && install -d -m 0755 /run/sshd /srv/www /srv/www/releases /opt/app/previous-release

COPY 99-lab.conf /etc/ssh/sshd_config.d/99-lab.conf
COPY entrypoint.sh /usr/local/sbin/app-entrypoint.sh
COPY www/ /srv/www/
COPY db-connection.env /opt/app/previous-release/db-connection.env
COPY appsvc-README.txt /home/appsvc/README.txt

RUN set -eux; \
    chown -R root:root /srv/www; \
    find /srv/www -type d -exec chmod 0755 {} \;; \
    find /srv/www -type f -exec chmod 0644 {} \;; \
    chown root:appsvc /opt/app /opt/app/previous-release /opt/app/previous-release/db-connection.env; \
    chmod 0750 /opt/app /opt/app/previous-release; \
    chmod 0640 /opt/app/previous-release/db-connection.env; \
    chown appsvc:appsvc /home/appsvc/README.txt; \
    chmod 0644 /home/appsvc/README.txt; \
    chmod 0755 /usr/local/sbin/app-entrypoint.sh; \
    chmod 0644 /etc/ssh/sshd_config.d/99-lab.conf

EXPOSE 22 8080
ENTRYPOINT ["/usr/local/sbin/app-entrypoint.sh"]
