# Backstage Merch: Coupon Reuse

`easy` · `web`

## Brief

Backstage Merch sells an Exclusive Digital Pass for `300` credits.
You have a customer account with `100` credits in its wallet.
Explore the shop and complete the purchase.

## Setup

Requires Docker with Docker Compose.
Run this command from the lab directory:

```bash
docker compose up -d
```

Open `http://localhost:8080/login`.
Sign in with `customer` / `Backstage2026!`.

## Goal

Buy the Exclusive Digital Pass and find the flag on the purchase confirmation.

Inside a full OpenLabs checkout, run this command from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

Enter the recovered flag when prompted.

## Reset

These commands clear your progress.
Stop the service before resetting it:

```bash
docker compose stop coupon-reuse
SECURE_MODE=0 docker compose run --rm --no-deps coupon-reuse python app.py reset
SECURE_MODE=0 docker compose up -d
```

Sign in again.
The wallet starts with `100` credits and the cart is empty.
