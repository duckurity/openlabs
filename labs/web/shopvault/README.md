# shopvault

`hard` · `web`

## Brief

ShopVault is an e-commerce REST API. Three accounts are seeded: a shopper, an administrator, and a manager. The manager's private reports hold the flag. No credentials are provided.

Ops note: seed account usernames are not the ones you'd expect.

## Setup

Run these from the lab directory:

```bash
docker compose up -d
```

The API listens on `http://localhost:8080`. All interaction is over HTTP; there is no web UI.

## Goal

Escalate from unauthenticated to the manager role and read the manager-only reports endpoint. Verify the solve from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

See [how to play](/play) for the usual solve loop.
