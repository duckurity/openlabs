# syntax=docker/dockerfile:1.7
# =============================================================================
# Dockerfile — ThreadLine API Challenge (Flask / Gunicorn / hardened runtime)
#
# BUILD POSTURE
#   Stage 1 (builder): installs deps into an isolated venv; build tools
#                      never reach the runtime image.
#   Stage 2 (runtime): python:3.12-slim + venv + app, owned by UID 1000.
#
# SECURITY POSTURE (enforced here; compose adds defense-in-depth)
#   * Non-root UID/GID 1000, nologin shell.
#   * tini as PID 1 — signal forwarding & zombie reaping.
#   * No pip cache, no bytecode (PYTHONDONTWRITEBYTECODE).
#   * Only curl + tini added beyond python-slim.
#   * FLAG is NOT in the image (runtime injection via env only).
#   * DB lives on a writable tmpfs (/data) — rootfs stays read-only.
# =============================================================================

############################
# STAGE 1 — BUILDER
############################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY src/requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

############################
# STAGE 2 — RUNTIME
############################
FROM python:3.12-slim

LABEL org.opencontainers.image.title="chal-api-bola" \
      org.opencontainers.image.description="CTF REST API challenge — BOLA + Business Logic" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    APP_HOME=/app \
    DB_PATH=/data/threadline.db

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 ctf \
 && useradd  --system --uid 1000 --gid ctf \
             --home-dir /home/ctf --create-home \
             --shell /usr/sbin/nologin ctf

COPY --from=builder /opt/venv /opt/venv

WORKDIR ${APP_HOME}
COPY --chown=ctf:ctf src/ .

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
 && chmod -R go-w /app \
 && mkdir -p /data && chown ctf:ctf /data

USER ctf:ctf

EXPOSE 1000

# Independent of business logic so a broken challenge route still
# reports lifecycle status accurately.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:1000/api/v1/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
