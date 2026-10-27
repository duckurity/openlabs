FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

RUN groupadd --gid 1000 ctf &&     useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin ctf

WORKDIR /app

COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app

RUN chown -R ctf:ctf /app
USER ctf

EXPOSE 8080

ENTRYPOINT ["python", "app.py"]
