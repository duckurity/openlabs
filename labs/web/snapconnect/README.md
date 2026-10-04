# SnapConnect

EASY · web

## Brief

SnapConnect is a small social app. Members get a profile with a handle, a bio, and an avatar, and everything runs through a GraphQL API at `POST /graphql`.

The app keeps a secret in `/var/www/flag.txt`. That path is outside the web root, so no URL reaches it. Read the file through the application and you have the flag.

Difficulty is easy. Expect to spend 15 to 30 minutes.

## Prerequisites

- GraphQL queries, mutations, and introspection
- The `graphql-multipart-request` format
- A tool that sends raw HTTP, such as `curl`, Burp, or Insomnia

## Setup

Start the lab:

```
 docker compose up -d --build
```

- App: `http://localhost:8081`
- Health: `http://localhost:8081/health.php`
- API: `POST http://localhost:8081/graphql`
- API reference: `http://localhost:8081/docs`

Registration is open. Create an account to get a session token.

## Goal

Read `/var/www/flag.txt` through the service. Verify your solve from the repository root:

```
python3 scripts/check.py labs/web/snapconnect
```

See [how to play](/play) for the usual solve loop.

## Reset

```
docker compose down -v
docker compose up -d --build
```

Reset clears uploads and sessions and reseeds the database.

## Flag format

`duck{...}` with lowercase letters, digits, and underscores between the braces.

## Rules

- The lab runs on your machine. Point your tools at `localhost:8081` only.
- No brute force is needed.
- Destroying the service is not the goal. The container resets anyway.
