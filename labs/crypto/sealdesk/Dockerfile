# syntax=docker/dockerfile:1
# check=error=true
FROM python:3.13.16-slim-bookworm@sha256:f040863673aea2570c3ff6a5c3fb4c673a016cbc5375005ad145915922b6b78a AS dependencies
WORKDIR /build
COPY requirements.txt ./
RUN python -m venv --without-pip /opt/venv \
    && python -m pip --python /opt/venv install --disable-pip-version-check \
       --no-cache-dir --require-hashes --only-binary=:all: -r requirements.txt

FROM python:3.13.16-slim-bookworm@sha256:f040863673aea2570c3ff6a5c3fb4c673a016cbc5375005ad145915922b6b78a AS runtime
LABEL org.opencontainers.image.title="SealDesk" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.openlabs.lab="sealdesk"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEALDESK_STATE_DIR="/run/sealdesk"
WORKDIR /opt/sealdesk
COPY --from=dependencies /opt/venv /opt/venv
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 entrypoint.sh gunicorn.conf.py ./
RUN chmod 0555 entrypoint.sh \
    && mkdir -p /run/sealdesk \
    && chown 10001:10001 /run/sealdesk \
    && chmod 0700 /run/sealdesk \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/lib/python3.13/ensurepip
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 \
    CMD ["python", "-B", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
ENTRYPOINT ["/opt/sealdesk/entrypoint.sh"]

FROM runtime AS test
COPY --chown=10001:10001 README.md reset.py ./
COPY --chown=10001:10001 tests ./tests
COPY --chown=10001:10001 scripts ./scripts
COPY --chown=10001:10001 solver ./solver
COPY --chown=10001:10001 ingress_proxy.py ./ingress_proxy.py
ENTRYPOINT ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
