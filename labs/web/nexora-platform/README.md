# nexora-platform

`medium` · `web`

## Brief

Nexora is a SaaS integration platform on GCP. Investigate the public app and
find a path to resources that should stay off the public edge.

## Setup

Run these from the lab directory:

```bash
docker compose up --build -d
```

Open `http://localhost:8080`. The OAST dashboard is on port `8081`.

## Goal

Reach the protected internal surface and recover the flag. Verify the solve
from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

## Reset

```bash
docker compose down -v
docker compose up --build -d
```
