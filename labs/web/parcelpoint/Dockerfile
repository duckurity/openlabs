FROM python:3.13.16-slim-bookworm@sha256:f040863673aea2570c3ff6a5c3fb4c673a016cbc5375005ad145915922b6b78a AS dependencies
WORKDIR /build
COPY requirements.txt ./
RUN python -m venv --without-pip /opt/venv \
    && python -m pip --python /opt/venv install --disable-pip-version-check \
       --no-cache-dir --require-hashes --only-binary=:all: -r requirements.txt

FROM python:3.13.16-slim-bookworm@sha256:f040863673aea2570c3ff6a5c3fb4c673a016cbc5375005ad145915922b6b78a AS runtime
LABEL org.opencontainers.image.title="ParcelPoint" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.openlabs.lab="parcelpoint"
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PARCELPOINT_STATE_DIR="/run/parcelpoint"
WORKDIR /opt/parcelpoint
COPY --from=dependencies /opt/venv /opt/venv
COPY app ./app
COPY database ./database
COPY entrypoint.sh gunicorn.conf.py ./
RUN chmod 0555 entrypoint.sh \
    && mkdir -p /run/parcelpoint \
    && chown 10001:10001 /run/parcelpoint \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/lib/python3.13/ensurepip
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"]
ENTRYPOINT ["/opt/parcelpoint/entrypoint.sh"]

FROM runtime AS test
HEALTHCHECK NONE
COPY tests ./tests
COPY scripts ./scripts
COPY solver ./solver
ENV PARCELPOINT_TEST_TMP="/tmp"
ENTRYPOINT ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
