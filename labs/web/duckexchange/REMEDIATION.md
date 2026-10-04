# DuckExchange Remediation Notes

This document describes the secure changes that should be made to the
challenge implementation if it is converted into a production service. The
deliberate vulnerabilities remain enabled in the training version.

## Blind SQL injection

The lookup query must never interpolate `ref` into SQL. Use a parameterized
query and escape wildcard characters if substring matching is required. For
example, the application can normalize the reference and pass it as a
PostgreSQL parameter:

```elixir
sql = """
SELECT doc_id
FROM challenge_lookup.delivery_index
WHERE 'IR-4472' ILIKE ('%' || $1 || '%')
LIMIT 1
"""

lookup_repo.query(sql, [ref])
```

If `%` and `_` must be treated as literal input, escape them before binding and
use an explicit `ESCAPE` clause. Input length and character policy should also
be enforced before the database call.

The least-privilege lookup role should remain in place as defense in depth,
but it is not a substitute for parameterization. SQL errors should be logged
internally with request correlation identifiers and returned as a generic
application response.

## Tenant authorization and transcoding

Authorization must use the same canonical tenant value that the handler uses.
The service should reject duplicate or conflicting tenant values in path and
query parameters, or configure the transcoder so that path bindings cannot be
overridden. A safer handler boundary is:

1. Parse the request once into a canonical structure.
2. Resolve the effective tenant.
3. Authorize that effective tenant against the session.
4. Load the document using the authorized tenant and document identifier.

Authorization tests must include direct cross-tenant paths, conflicting query
parameters, encoded duplicate parameters, and all supported HTTP transcoding
routes.

## Session and OTP flow

Do not create a trusted session before the second factor is verified. Issue a
pre-authentication transaction identifier with a narrow scope, then replace it
with an authenticated session only after successful OTP verification. Set
`Secure`, `HttpOnly`, and an appropriate `SameSite` policy, rotate tokens after
authentication, and invalidate pending transactions after timeout or repeated
failure.

## Secret handling

Flags and production secrets must be injected through a secret manager or
runtime secret mount. They must not be committed in source, Compose
environment values, images, static files, logs, error pages, or test fixtures.
The challenge uses a mounted Docker secret for this reason.

## Retest criteria

After remediation:

- SQL metacharacters are treated as data and cannot change the predicate.
- An Acme session receives `403` for every Initech document request,
  regardless of query-string overrides.
- The OTP session cannot access authenticated resources before verification.
- The runtime flag is present only in the lab-controlled secret and in a
  successful authorized response.
