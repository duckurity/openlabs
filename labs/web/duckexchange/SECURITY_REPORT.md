# DuckExchange Security Report

## 9.1 Executive summary

DuckExchange is an isolated tenant document-review application. Its primary
training weakness is an authorization mismatch in the gRPC 0.11 HTTP
transcoder: query parameters can override the tenant field after middleware
has authorized the path tenant. A restricted blind SQL injection is the
secondary chain component used to recover the document UUID. The runtime-only
flag is appended only after the gRPC authorization boundary is crossed.

The learning objective is to combine API reconnaissance, protobuf/request
field reasoning, and authorization testing. Least-privilege blind extraction
supports the chain without becoming the primary lesson. A supporting
authentication lesson covers session/token lifecycle: a pre-OTP token and its
cookie path are not substitutes for completed verification or server-side
authorization.

## 9.2 Challenge overview

The application supports account registration, login, a fake OTP checkpoint,
an Acme inbox, an external-delivery lookup, and a document API. The primary
vulnerability is gRPC/API authorization confusion caused by path/query field
precedence in the HTTP transcoder. The secondary vulnerability is blind SQL
injection in the restricted delivery lookup. The pre-OTP session cookie is a
supporting authentication/session-lifecycle lesson and intended discovery
step, not an independent flag path.

Difficulty is medium, with an expected solve time of 30–60 minutes for a
participant comfortable with HTTP tooling.

## 9.3 Architecture and trust boundaries

```text
Player HTTP client
        |
        v
  nginx :4000
    |             \
    v              v
 Phoenix web     gRPC document endpoint :50051
    |              |
    +-------> PostgreSQL :5432
                    |\
                    | +-- application Repo: tenants, users, documents, sessions
                    +---- lookup Repo: challenge_lookup.delivery_index only
```

The player-controlled session is an Acme analyst session. The web layer and
document service share the application database, but the external lookup uses
the low-privilege `tenant_exchange_lookup` role. The flag is a runtime secret
mounted into the app container and is not a database value.

## 9.4 Attacker starting point

The attacker has only the assigned HTTP URL and can self-register an analyst
account. No seeded credentials, source code, database credentials, Docker
socket, host filesystem, or external services are in scope. The account is
authorized for `acme-corp` only.

## 9.5 Attack surface

Relevant HTTP operations are:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET/POST | `/register` | Create the player account |
| GET/POST | `/login` | Create the pre-OTP session |
| GET/POST | `/otp` | Nonfunctional OTP checkpoint |
| GET | `/inbox` | Acme dashboard and observable references |
| GET | `/exchange/lookup?q=...` | Boolean delivery lookup |
| GET | `/api/v1/tenants/{tenant_id}/documents/{doc_id}` | Transcoded document retrieval |
| GET | `/docs/` | Deliberately published recon artifacts |

The document route accepts a path tenant and a protobuf request assembled by the
gRPC HTTP transcoder. The guard reads the route binding; the handler reads the
final request object.

## 9.6 Vulnerability description

### Tenant authorization confusion

The middleware compares the session tenant to the path binding. For this
empty-body transcoded route, query parameters can override the protobuf
`tenant_id` after the middleware has authorized the request. The failed control
is authorization over a non-canonical request representation.

### Blind SQL injection

The lookup builds SQL by interpolating the `q` value into a `LIKE`-style
predicate. The failed control is input separation. The query is executed with
a role that can read only `challenge_lookup.delivery_index(doc_id)`, which
limits the intended impact and keeps the flag out of SQL. This is a secondary
identifier-discovery step for the primary gRPC authorization issue.

### Supporting session behavior

Login sets a trusted cookie before the fake OTP is complete and scopes it to
`/otp`. This forces deliberate cookie capture and manual reuse. OTP brute force
is disabled and is not an alternate solution.

## 9.7 Intended attack path

1. Register an Acme analyst and log in.
2. Capture `tv_session` from the login response and manually send it to
   `/inbox`.
3. Inspect the inbox and published artifacts to identify `IR-4472`, the
   `doc_id` projection, and the document route.
4. Submit boolean SQL predicates through `q` and recover the current UUID one
   character at a time as the secondary discovery step.
5. Request the UUID on the Initech path and observe `403 tenant denied`.
6. Request the same UUID on the Acme path with `tenant_id=initech-inc` in the
   query string, exploiting the primary gRPC authorization mismatch.
7. Observe the restricted document response and its runtime flag marker.

## 9.8 Impact assessment

- Confidentiality: a low-privilege Acme analyst can retrieve a restricted
  document belonging to Initech.
- Integrity: the lookup role has no write privilege; the challenge does not
  demonstrate data modification.
- Availability: no availability impact is intended; stacked writes and
  destructive operations are outside the challenge path.
- Privilege: the attacker does not become an Initech user, but bypasses the
  document tenant boundary for one recovered identifier.

## 9.9 Flag retrieval

The flag is read from the lab's mounted Docker secret at runtime. It is appended
only for the restricted incident document. A valid solve therefore requires
both the UUID recovered from the lookup oracle and the query/path mismatch that
causes the handler to load the Initech tenant while the guard sees Acme.

Sanitized success evidence is:

```http
GET /api/v1/tenants/acme-corp/documents/<recovered-uuid>?tenant_id=initech-inc
Cookie: tv_session=<player-session>
```

```json
{
  "tenantId": "initech-inc",
  "classification": "restricted",
  "title": "Incident IR-4472 Escalation",
  "body": "... Flag: <CONTROLLED_FLAG>"
}
```

## 9.10 Root cause

The lookup root cause is string concatenation of untrusted input into SQL.
The authorization root cause is checking one representation of a request and
executing another after query parameters are merged into the transcoded
protobuf. The session root cause is treating a pre-verification token as a
trusted session.

## 9.11 Remediation

Parameterize and validate the lookup input, preserve the lookup role's least
privilege, and reject or canonicalize conflicting path/query tenant values.
Authorize the exact tenant used for the database lookup. Move session creation
after OTP verification and use a separate pending-authentication token. Keep
the runtime flag in a secret manager or runtime secret mount. Detailed secure
implementation guidance is in `REMEDIATION.md`.

## 9.12 Verification and retest

The vulnerable behavior is covered by ExUnit tests for the boolean oracle,
document response, session flow, and transcoder precedence. The end-to-end
validator checks deployment, public routes, direct cross-tenant denial, UUID
recovery, and the final runtime flag marker. Run:

```sh
./tools/validate.sh
```

Expected secure retest results after remediation are parameterized lookup
input, `403` for conflicting tenant requests, and no trusted access before
OTP verification.

## 9.13 Unintended attack paths

Testing found and handled these risks:

- Old tests referenced application-table columns that are intentionally not
  visible to the lookup role; they were updated to the published projection.
- The restricted UUID is not hardcoded in the player workflow; seed UUIDs are
  generated and must be recovered after reset.
- The flag was removed from Compose defaults, configuration fallbacks, and
  evidence examples. It is now supplied through a runtime secret file.
- The debug controller is not routed.
- The published docs are intentional recon artifacts and contain no runtime
  flag or database password needed by players.

No alternative flag-retrieval path is intended. Equivalent clients and
proxies that send the same requests are considered the same solution.

## 9.14 Conclusion

The challenge demonstrates how a constrained blind oracle can still disclose a
security-sensitive identifier, and how authorization can fail when middleware
and a handler do not share a canonical request representation. The controlled
runtime flag makes the intended boundary crossing observable without placing a
secret in source or database content. Docker Compose reset, health checks,
tests, and the validator provide reproducible operation in the isolated
training environment.

## Evidence index

- Player behavior: `README.md`
- Deployment/reset: `DEPLOYMENT.md`
- Intended solution: `WRITEUP.md` and `ORGANIZER.md`
- Automated evidence: `tools/validate.sh` and `tools/validate_challenge.py`
- Application tests: `tenant_exchange/test/`
