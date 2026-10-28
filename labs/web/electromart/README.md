# 1. Challenge Name

**ElectroMart eCommerce website CTF**

# 2. Scenario

ElectroMart recently introduced a new customer-support assistant to help keep the storefront running smoothly during its summer promotion.

The assistant operates through a real browser session, periodically signing in, browsing products, reviewing customer feedback, and following links it encounters during its routine visits.

Behind the scenes, the engineering team also maintains an internal diagnostics service to investigate unusual browser activity that ordinary application logs might miss.

The latest release passed its basic functional tests, and nothing appears unusual during normal use. However, the team has noticed behavior that cannot be fully explained by its existing monitoring tools.

You have access to the storefront as a regular customer. Investigate the application, understand how its different components interact, and determine whether the support assistant's account exposes something it should not.


# 3. Objective

Take over the seeded victim account and retrieve the flag from the victim's profile.

# 4. Difficulty

**Hard**

# 5. Prerequisites

- HTTP basics: requests, responses, headers, status codes, and URL encoding
- Cookies, sessions, and browser storage
- JavaScript and browser DevTools
- Reflected/DOM-based XSS and Content Security Policy (CSP)
- Out-of-band application security testing (OAST)
- Basic Docker Compose commands
- Familiarity with Burp Suite, curl, or an equivalent HTTP proxy

# 6. Startup Instructions

Requirements: Docker with the Compose plugin.

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. (optional) Edit `.env` and set at least a strong `MONGO_INITDB_ROOT_PASSWORD` and a random `SESSION_SECRET`.

3. Build and start the lab:

   ```bash
   docker compose up -d --build
   ```

4. Check that the services are healthy:

   ```bash
   docker compose ps
   docker compose logs -f bot
   ```

   The app is ready when `app` is healthy. The victim bot starts automatically after the app and OAST are healthy, then runs continuously.

5. Stop the lab without deleting data:

   ```bash
   docker compose stop
   ```

6. Start it again:

   ```bash
   docker compose up -d
   ```

# 7. Connection Information

| Service | Address |
| --- | --- |
| Storefront | `http://localhost:3000` |
| OAST dashboard | `http://127.0.0.1:4000` |
| OAST JSON API | `http://127.0.0.1:4000/api/...` |
| Internal OAST callback origin | `http://attckerserver.local:4000` |
| Internal app origin used by the bot | `http://app.test:3000` |




# 8. Reset Instructions

The lab resets automatically whenever the app starts, restoring the victim and flag and removing non-victim accounts, carts, user reviews, and stale sessions.

Reset the app and clear OAST interactions:

```bash
docker compose restart
```

Recreate the stack while keeping the database volume:

```bash
docker compose down
docker compose up -d --build
```

Perform a full wipe, including the database and bot artifacts:

```bash
docker compose down -v
docker compose up -d --build
```

OAST interactions are held in memory, so they are cleared whenever the OAST container restarts. If you set `LAB_RESET_ON_BOOT=false` in `.env`, reset manually with:

```bash
docker compose exec app node src/reset.js
```

# 9. Flag Format

```text
duck{***_**_******************}
```
