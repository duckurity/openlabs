# MarketNest CTF — Deployment and Setup Guide

This document is for the challenge author or hosting platform. Players should
receive only the running black-box service, not this file, the source tree, or
the author walkthrough.

## 1. Challenge identity

Application name: **MarketNest**

Local URL:

```text
http://localhost:8088/login
```

The production flag for this challenge is:

```text
duck{jku_1nj3ct10n_t0_sp3L_1nj3ct10n_rc3_gr4nt3d_012xajd}
```

This is the real flag and must be the value printed by `/app/flagbinary` in
the deployed image. Do not deploy a test flag.

## 2. Required build files

The Docker build requires:

```text
Dockerfile
pom.xml
src/
```

The source tree contains the Spring Boot application, templates, static assets,
and the native flag helper.

`compose.yaml` is optional and is only needed when the hosting platform uses
Docker Compose. The author documents are not needed inside the runtime image:

```text
README.md
walkthrough.md
SETUP.md
```

Do not include player-created private keys, JWTs, Burp project files, or local
`jwks.json` files in the deployment package.

## 3. Flag source and verification

The flag source is:

```text
src/main/c/priceforge_flag.c
```

The flag is XOR-obfuscated in the C source and is compiled into the native
executable. It is not stored as `/flag.txt`.

The Dockerfile compiles it with:

```dockerfile
RUN gcc -O2 -s -o /app/flagbinary src/main/c/priceforge_flag.c
```

The intended container path is:

```text
/app/flagbinary
```

Before deployment, confirm that the encoded bytes in
`src/main/c/priceforge_flag.c` decode to the real flag above. If they decode to
an old test flag, replace the encoded byte array with bytes generated from the
real flag, rebuild the image, and test again. Never leave the test flag in a
production event image.

## 4. Build the image

From the directory containing `Dockerfile`:

```powershell
docker build -t marketnest-ctf:latest .
```

Or use Compose:

```powershell
docker compose build
```

The build performs two important operations:

1. Maven packages the Spring Boot application.
2. GCC compiles `priceforge_flag.c` into `/app/flagbinary`.

## 5. Run locally with the intended restrictions

Using Compose:

```powershell
docker compose up -d
```

The supplied Compose configuration publishes:

```text
localhost:8088 -> container:8080
```

It also enables:

- Read-only container filesystem
- Dropped capabilities
- `no-new-privileges`
- Restricted `/tmp` tmpfs
- Process and memory limits

The application should then be available at:

```text
http://localhost:8088/login
```

## 6. Basic health checks

Check the container:

```powershell
docker ps
```

Check the login page:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8088/login
```

Expected result:

```text
HTTP 200
```

Check that an unauthenticated protected route redirects:

```powershell
Invoke-WebRequest -UseBasicParsing `
  http://localhost:8088/dashboard `
  -MaximumRedirection 0 `
  -ErrorAction SilentlyContinue
```

Expected result:

```text
HTTP 302
Location: http://localhost:8088/login
```

Check the sample CSV resource:

```powershell
Invoke-WebRequest -UseBasicParsing `
  http://localhost:8088/templates/bulk_import_sample.csv
```

Expected result:

```text
HTTP 200
```

## 7. Verify the final flag path

The safest author verification is to run the helper inside a temporary
container from the freshly built image and inspect only its output:

```powershell
docker run --rm --entrypoint /app/flagbinary marketnest-ctf:latest
```

The output must be exactly:

```text
duck{jku_1nj3ct10n_t0_sp3L_1nj3ct10n_rc3_gr4nt3d_012xajd}
```

If the output is different, stop deployment. Update
`src/main/c/priceforge_flag.c`, rebuild the image without relying on stale
layers, and repeat this check.

For a clean rebuild:

```powershell
docker compose down
docker build --no-cache -t marketnest-ctf:latest .
docker compose up -d
```

## 8. End-to-end smoke test

Perform these checks before handing the challenge to a CTF platform:

1. Create a new account.
2. Log in and confirm the normal dashboard loads.
3. Confirm `/import` redirects for a retailer.
4. Confirm a forged administrator token reveals Pricing Studio.
5. Upload:

   ```csv
   name,basePrice,stock,priceFormula
   Test,10,1,7*7
   ```

   The computed value should be `49.0`.

6. Upload `'abc'.length()` and confirm the result is `3`.
7. Confirm the direct `Runtime` expression is rejected by the blacklist.
8. Confirm the reflective bypass reaches command execution.
9. Confirm `/bin/ls -al` reveals `flagbinary`.
10. Execute `./flagbinary` through the intended output-reader payload.
11. Confirm the real flag appears in the computed-price cell.

Use a fresh `/import` page before every upload because CSRF tokens are
one-time. Use fresh accounts and tokens after every container restart because
the application stores users and JWT signing keys in memory.

## 9. Platform deployment checklist

Before deployment:

- Build from a clean source tree.
- Confirm `/app/flagbinary` prints the real flag.
- Do not expose author documents to players.
- Do not include private keys or local JWKS files.
- Publish only the challenge URL and player instructions.
- Keep the container isolated from other challenge services.
- Preserve the read-only and capability restrictions.
- Confirm the platform allows the target container to reach player-hosted JWKS
  URLs if the local `jku` stage is part of the event.
- Confirm outbound network policy is compatible with the intended JWKS stage.
- Restart the instance between events if clean in-memory state is required.

## 10. Stop and reset

Stop the local instance:

```powershell
docker compose down
```

Start a fresh instance:

```powershell
docker compose up -d
```

Accounts, orders, sessions, and server JWT keys are held in memory, so a
container restart resets the challenge state.
