FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/backstage.sqlite3 \
    SECURE_MODE=0

WORKDIR /app

COPY app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 backstage \
    && useradd --uid 10001 --gid backstage --no-create-home backstage \
    && mkdir /data \
    && chown backstage:backstage /data \
    && chmod 700 /data

COPY --chown=backstage:backstage app/ /app/

USER 10001:10001

EXPOSE 5000

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).close()"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "/dev/null", "app:create_app()"]
