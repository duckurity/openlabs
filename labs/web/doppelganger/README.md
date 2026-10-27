# doppelganger

`medium` · `web`

## Brief

Secured Notes is a shared note service with a private administrator review bot. Submit JSON notes, and make the administrator's browser hand you its session value.

## Setup

Run these from the lab directory:

```bash
docker compose up -d --build
```

Open `http://localhost:5000`. The review bot starts with the stack and checks notes roughly every 10 to 20 seconds. Captured reviews appear at `http://localhost:5000/api/solved`.

The inbox token is shown on the page. Reset the lab with:

```bash
docker compose down -v
```

## Goal

Recover the administrator's session value and read the flag. The flag has the form `duck{...}`.
