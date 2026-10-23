# FieldOps 360

MEDIUM · web

## Brief

FieldOps 360 is a field service platform for trade companies. Tenants manage
jobs, customers, and outbound email from one portal. The platform reports
opens on every message it sends.

You hold a sandbox account for one tenant. The credentials are on the login
page.

## Setup

Start the lab:

```
docker compose up -d --build
```

Open `http://localhost:8080`.

## Goal

Recover the flag from the admin export.

Verify the solve:

```
python3 scripts/check.py labs/web/fieldops-360
```

See [how to play](/play) for the usual solve loop.
