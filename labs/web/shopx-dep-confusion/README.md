# shopx-dep-confusion

`HARD` · `web`

## Brief

ShopX moved its storefront build pipeline to npm earlier this year. You
have been handed access to the public storefront ahead of a security
assessment. Nothing else. Investigate the surface, follow what it tells
you, and reach the protected flag.

## Setup


Open `http://localhost:8080`.

Everything the lab needs runs inside the compose network. Nothing reaches
outside it.

## Goal

Retrieve the flag held by ShopX's internal billing service.

Check a solve from the repository root:

```bash
python3 scripts/check.py labs/web/shopx-dep-confusion
```
