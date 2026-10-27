# DuckBot — The Helpful Assistant

## Brief
DuckBot is a lightweight customer-support chatbot running in an isolated CTF environment.
The assistant has internal instructions containing a secret flag. The application is intentionally vulnerable to prompt injection, allowing a user to manipulate the assistant into disclosing information that should remain private.

## Setup
Build and start the challenge:

```bash
docker compose up --build
```

The challenge is available at:

```text
http://localhost:8080
```

## Goal
Interact with DuckBot and obtain the hidden flag through prompt injection.

## Scope
This challenge is self-contained and does not require an external LLM, API key, database, or Internet access.

## Intended Technique
Prompt Injection / System Prompt Leakage.

## Evidence
A successful submission should include:
- The request/prompt used to manipulate DuckBot.
- The relevant chatbot response containing the flag.
- A concise explanation of why the secret was exposed.
