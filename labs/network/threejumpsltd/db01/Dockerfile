FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server postgresql sudo iproute2 netcat-openbsd ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system dbmaint \
    && useradd --create-home --user-group --shell /bin/bash --groups dbmaint dbops \
    && echo 'dbops:Inv3ntory_Read_2026!' | chpasswd \
    && install -d -m 0755 /run/sshd /opt/dbops /var/backups/db

COPY 99-lab.conf /etc/ssh/sshd_config.d/99-lab.conf
COPY entrypoint.sh /usr/local/sbin/db-entrypoint.sh
COPY db-maintenance /usr/local/sbin/db-maintenance
COPY rotate.sh /opt/dbops/rotate.sh
COPY dbops-maintenance.sudoers /etc/sudoers.d/dbops-maintenance

RUN set -eux; \
    PG_VERSION="$(ls /etc/postgresql | sort -V | tail -n1)"; \
    sed -ri "s/^#?listen_addresses[[:space:]]*=.*/listen_addresses = '*'/" "/etc/postgresql/${PG_VERSION}/main/postgresql.conf"; \
    printf '\nhost inventory inventory_app 172.28.30.0/24 scram-sha-256\n' >> "/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"; \
    chown root:root /usr/local/sbin/db-maintenance /usr/local/sbin/db-entrypoint.sh; \
    chmod 0755 /usr/local/sbin/db-maintenance /usr/local/sbin/db-entrypoint.sh; \
    chown root:dbmaint /opt/dbops/rotate.sh; \
    chmod 0775 /opt/dbops/rotate.sh; \
    chmod 0440 /etc/sudoers.d/dbops-maintenance; \
    visudo -cf /etc/sudoers.d/dbops-maintenance; \
    chmod 0644 /etc/ssh/sshd_config.d/99-lab.conf; \
    printf 'duck{Root_Access}\n' > /root/flag.txt; \
    chown root:root /root/flag.txt; \
    chmod 0600 /root/flag.txt

EXPOSE 22 5432
ENTRYPOINT ["/usr/local/sbin/db-entrypoint.sh"]
