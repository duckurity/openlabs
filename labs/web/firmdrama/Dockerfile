FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55

WORKDIR /opt/firmdrama

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

COPY src/requirements.txt ./src/requirements.txt

# Install and remove Python build tools in one layer. MySQL core packages avoid
# initializing a build-time database that the runtime tmpfs would hide.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
        mysql-server-core-8.0 mysql-client-core-8.0 mysql-common ca-certificates procps \
    && pip3 install --break-system-packages --no-cache-dir -r ./src/requirements.txt \
    && apt-get purge -y python3-pip python3-setuptools python3-wheel \
    && rm -rf /var/lib/apt/lists/* /usr/lib/python3.12/ensurepip /root/.cache

RUN groupadd --system --gid 10001 firmdrama \
    && useradd --system --uid 10001 --gid firmdrama --home-dir /opt/firmdrama --shell /usr/sbin/nologin firmdrama \
    && install -d -o 10001 -g 10001 -m 0750 /var/lib/mysql-files

COPY database ./database
COPY src ./src
COPY scripts ./scripts
COPY solver ./solver
COPY tests /opt/firmdrama-tests
COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh scripts/*.sh \
    && mkdir -p /home/olivia/DoNotOpenThisFolder \
    && chown -R root:root /opt/firmdrama

EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

USER firmdrama
CMD ["/opt/firmdrama/entrypoint.sh"]
