# DuckExchange Challenge Design

## 1. Challenge identity

- Name: DuckExchange
- Category: Web application security
- Difficulty: Medium
- Estimated solve time: 30–60 minutes
- Primary vulnerability family: API Infrastructure & Protocol Issues — gRPC
  Security
- Secondary family: Input Validation & Injection — blind SQL injection
- API-chain role: the SQL injection is a controlled identifier-discovery step;
  the main learning objective is the gRPC request/authorization mismatch
- Related coverage: API Recon & Enumeration and API Chaining
- Supporting authentication lesson: session/token lifecycle and the difference
  between pre-authentication state and authorization

The primary issue is the gRPC 0.11 HTTP-transcoding override: authorization
decisions use the HTTP path tenant while the transcoded request can receive a
different query tenant. Blind SQL injection is used only to recover the
document identifier needed to reach that API boundary.

## 2. Learning objective

The participant should learn to discover and inspect an API contract, reason
about gRPC HTTP-transcoding and field precedence, and test whether an
authorization decision is made over the same canonical request fields that
reach the application handler. A bounded boolean SQL injection oracle supports
identifier discovery, but it is deliberately secondary to the API security
lesson. The flag is emitted only after the participant crosses the intended
tenant authorization boundary.

The challenge also teaches a supporting authentication lesson: a token issued
before OTP completion is not proof that the user has completed verification,
and a cookie's URL path controls browser delivery but does not replace
server-side authorization. This behavior enables the workflow discovery step;
it is not a separate flag-retrieval path.

## 3. Believable scenario

DuckExchange is an internal delivery-review application used by legal and
incident-response teams. Analysts can review their own tenant's inbox and can
check whether an external delivery reference is still routed for ownership
review. A separate low-privilege database role supports that lookup. Document
retrieval is exposed through a versioned HTTP API backed by a gRPC service.

An incident packet for another tenant is sealed until tenant ownership is
verified. The participant must recover that packet through the observable
application workflow.

## 4. Attacker starting point and assumptions

The participant starts with:

- Network access to one isolated HTTP challenge instance.
- No source code, database credentials, seeded credentials, or host access.
- The ability to create a normal analyst account through the public
  registration workflow.
- A browser, an HTTP client, or an intercepting proxy.

The participant is not expected to access the seeded Initech account. The
player-controlled account belongs to `acme-corp` and has no direct access to
the restricted Initech document.

## 5. Intended attack path before implementation

1. Register and log in as an Acme analyst.
2. Notice that login creates a trusted session before the fake OTP step is
   completed. Capture the cookie from the login response and manually reuse it
   because its browser path is `/otp`.
3. Use the inbox and published application artifacts to learn the external
   reference, database projection, and transcoded document route.
4. Exercise the delivery lookup as a boolean oracle. Use a controlled,
   character-by-character query to recover the UUID from the low-privilege
   delivery projection. This is the controlled secondary injection step.
5. Inspect the published API descriptor and test the document route's path and
   query representations of `tenant_id`.
6. Confirm that the recovered document is denied when the path names
   `initech-inc`.
7. Keep the authorized `acme-corp` path but supply `tenant_id=initech-inc` as a
   query parameter. The guard authorizes the path tenant while the handler
   receives the query-overridden tenant. This gRPC authorization mismatch is
   the primary vulnerability and learning outcome.
8. Retrieve the restricted document. The runtime-only flag is appended only in
   this restricted response.

## 6. Intentional implementation

The application intentionally contains these challenge behaviors. The first
two items are the primary API/protocol vulnerability; the SQLi item is a
controlled secondary chain component:

- The gRPC HTTP transcoder allows query values to override path-derived
  protobuf fields for the empty-body route.
- `TenantGuard` checks the route binding, while `DocumentServer` trusts the
  final request tenant.
- The delivery query interpolates the user-controlled reference into a query
  executed by `tenant_exchange_lookup`.
- That database role can read only
  `challenge_lookup.delivery_index(doc_id)`, which turns the injection into a
  bounded UUID oracle rather than unrestricted application-table access.
- A trusted pre-OTP session cookie is issued with `Path=/otp` to support the
  API workflow and manual cookie-reuse discovery.

The public build/schema/descriptor artifacts are a deliberate recon aid. They
are exposed through the challenge proxy and contain no flag or credentials
needed to access the database.

## 7. Flag condition

The flag is read from the lab's Docker secret source at response time. It is
not in the database, image, public artifacts, or the restricted document row.
The document service appends it only when the restricted `Incident IR-4472
Escalation` document is returned. Therefore a successful flag response proves
that the participant obtained the document UUID and crossed the tenant
authorization boundary.

## 8. Noise control and excluded paths

- The lookup role has no write privileges and no access to application tables.
- The seeded Initech login has a random password and is not a solution path.
- The OTP endpoint does not accept a code and rate-limits attempts, removing
  brute force as a competing path.
- The flag is not returned by the lookup endpoint or normal Acme document
  responses.
- Debug code is not routed or exposed.
- The challenge performs no outbound requests and has no persistence outside
  its Compose volume.

The session behavior is a supporting intended discovery step, not a second
flag path. The only intentional alternatives are equivalent HTTP clients or
proxies that reproduce the same requests.

## 9. Determinism, reset, and isolation

The seed operation is idempotent by tenant/document identity and inserts the
restricted delivery UUID before realistic decoy UUIDs. UUID values may change
after a full reset, so the participant must recover the current value rather
than rely on a hardcoded identifier. The flag condition and response markers
are stable.

`docker compose down -v` removes the database volume and sessions. A subsequent
deployment recreates the schema and seed data from the submitted files. The
flag is mounted afresh from the lab's secret source.

## 10. Validation plan

- Compose configuration is checked with an operator-provided secret file.
- `tools/validate.sh` checks public health endpoints, authorization behavior,
  the boolean oracle, UUID recovery, direct denial, query override, and the
  runtime-only flag marker.
- `MIX_ENV=test mix test` covers account/session behavior, document storage,
  the oracle, gRPC request precedence, and web flows.
- A clean reset is validated by deleting the Compose volume and rerunning the
  same checks.

## 11. Deliverable mapping

| Requirement | Submitted material |
| --- | --- |
| Player instructions | `README.md` |
| Deployment and reset | `DEPLOYMENT.md`, `docker-compose.yml` |
| Design rationale | `CHALLENGE_DESIGN.md` |
| Technical security report | `SECURITY_REPORT.md` |
| Remediation | `REMEDIATION.md` |
| Official solution | `WRITEUP.md`, organizer notes |
| Automated validation | `tools/validate.sh`, `tools/validate_challenge.py`, ExUnit tests |
| Controlled flag | Evaluator-provided file mounted as a Docker secret |
