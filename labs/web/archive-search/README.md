# Archive Search

## Brief

Archive Search is an internal catalog for staff to search archived product records.
The application and account are fictional training material.

Open `http://127.0.0.1:8080/`. The host port is `8080`.
Sign in with username `researcher` and password `Archive2026-researcher`.

## Setup

From the repository root:

```sh
cd labs/web/archive-search
docker compose up --build -d
docker compose ps
```

Wait for the `web` service to become healthy. Dependencies are installed during
the image build. The running lab does not require an external service.

## API endpoints

| Method | Path |
|---|---|
| GET | `/` |
| GET | `/health` |
| POST | `/api/login` |
| GET | `/api/me` |
| GET | `/api/products` |
| GET | `/api/search` |
| POST | `/api/logout` |

## Goal

Recover the lab flag in `duck{...}` format. Submit the complete string, including
the braces. The repository checker compares its SHA-256 hash with `lab.yml`.

## Reset

From this lab directory:

```sh
docker compose stop web
docker compose run --rm --no-deps web python manage.py reset
docker compose up -d
```

Reset restores the starter data and preserves the fixed submission flag.
Use `docker compose down -v` to remove the lab containers and stored data.
