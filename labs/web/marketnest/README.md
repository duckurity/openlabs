# MarketNest

**Category:** Web  
**Difficulty:** Hard  
**Flag format:** `duck{...}`  
**Estimated time:** 60–90 minutes

## Brief

MarketNest is a B2B inventory management platform for small retailers. Retailers manage a catalog, orders, and inventory from a normal workspace. A separate Pricing Studio allows bulk-importing product catalogs via CSV, with a `priceFormula` column for computed pricing.

The Pricing Studio is not visible to normal users. The import accepts formulas and evaluates them server-side. The flag is not stored as a readable file; it lives inside a native executable.

## Goal

Gain access to the Pricing Studio, exploit the formula evaluation to achieve code execution, discover and execute the flag binary to retrieve the flag.

## Setup

For a hosted instance, use the challenge URL provided by the organizer.

For a local copy, start the lab from this directory:

```sh
docker compose up -d
```

Then open `http://127.0.0.1:8088`.

Create an account and sign in. Source code and access to the host are not required.

## Reset

For a hosted instance, ask the organizer to reset the challenge. For an authorized local deployment, reset it with:

```sh
docker compose down -v
docker compose up -d --build
```

Do not edit the application source or database files by hand.

## Rules

- Test only the assigned challenge instance.
- Do not attack the host, Docker daemon, other containers, or external systems.
- Do not run denial-of-service or destructive tests.
- Keep any recovered flag and account credentials private.
