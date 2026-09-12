# Northstar Document Hub

## Scenario

This is a fictional company called Northstar. It has a simple internal system for storing project documents and approvals. You are given a training analyst account that you can use to access the website and its API.

## Objective

You need to find the flag by exploring the website and its API while logged in with your account.

**Difficulty:** Easy - Medium
**Expected Time:** About 20-30 minutes
**Flag Format:** `SK-CTF{...}`

## Before You Start

You need Docker Desktop with Docker Compose v2, and a normal browser or a tool like Postman.

## Running

From inside the folder, run:

```bash
docker compose up --build
```

Open http://localhost:3000

## Login Credentials

| Username    | Password   |
| ----------- | ---------- |
| `alex.ward` | `Maple!47` |

## Rules

The challenge is limited to `localhost:3000` only - do not try to access anything else.

Do not use Docker or access the server files or database. Use only the website and its API.
