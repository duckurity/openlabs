# cloudvault

`hard` · `web`

## Brief

CloudVault is a document-ingestion platform. The API accepts URLs and imports documents from them. A low-privileged account is seeded. Retrieve the flag hidden in the CloudVault environment.

## Setup

Run these from the lab directory:

```bash
docker compose up -d
```

The GraphQL API listens on `http://localhost:8080/graphql`. A seeded account is provided:

- Username: `player`
- Password: `changeme123`

## Goal

Authenticate and explore the API. Retrieve the flag. Verify the solve from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

See [how to play](/play) for the usual solve loop.
