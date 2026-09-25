# Nexora platform

`medium` · `web`

## Brief

Nexora is a SaaS integration and developer platform hosted on Google Cloud
Platform. Investigate the public application and find a path to resources
that should stay off the public edge.

## Setup

Run this from the lab directory:

```bash
docker compose up --build -d
```

Open `http://localhost:8080` for the application. The local OAST dashboard
is on `http://localhost:8081`.

## Goal

Reach the protected internal surface and recover the flag. Verify from the
repo root when you have a candidate:

```bash
python3 scripts/check.py labs/web/nexora-platform
```

## Reset

```bash
docker compose down -v
docker compose up --build -d
```
