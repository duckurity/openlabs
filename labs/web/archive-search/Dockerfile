FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/srv/data
WORKDIR /srv
COPY app/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 lab \
    && useradd --uid 10001 --gid lab --no-create-home lab \
    && mkdir /srv/data \
    && chown lab:lab /srv/data
COPY app/app/ ./app/
COPY app/seed.py app/manage.py app/app.py ./
USER 10001:10001
EXPOSE 8080
CMD ["python", "app.py"]
