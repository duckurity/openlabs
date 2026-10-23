# DuckExchange Deployment Checklist

The lab's controlled flag is kept in `app/flag.txt` and mounted as a Docker
secret. The application reads it only at runtime; it is not copied into the
application image or exposed as an environment variable.

Start the challenge:

```sh
docker compose up -d --build
```

The checked-in secret source is intentionally inside this isolated lab because
the repository needs a reproducible local deployment. Do not reuse it outside
the assigned training environment.

Health check:

```sh
curl http://127.0.0.1:4000/
curl http://127.0.0.1:4000/login
curl -i http://127.0.0.1:4000/inbox
curl http://127.0.0.1:4000/docs/
./tools/validate.sh
```

Give players only the deployed URL and `README.md`.

Do not give players:

- Source code.
- `ORGANIZER.md`.
- `DEPLOYMENT.md`.
- `Dockerfile`.
- `docker-compose.yml`.
- `nginx.conf`.
- The writeup.

Reset local state:

```sh
docker compose down -v
docker compose up -d --build
```
