# ---------- ElectroMart persistent Victim Bot image ----------
# The official Playwright image already contains the exact Chromium build that
# matches the pinned playwright package, so the bot service does not need to
# download a browser at build time.
FROM mcr.microsoft.com/playwright:v1.64.1-noble

ENV NODE_ENV=production \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

COPY --chown=pwuser:pwuser src ./src

# Screenshot/diagnostic output lives in a controlled directory. The named
# Compose volume inherits this ownership when it is first created.
RUN mkdir -p /app/bot-artifacts/screenshots \
    && chown -R pwuser:pwuser /app/bot-artifacts

USER pwuser

# No shell wrapper: Node is the container process and receives Docker's
# SIGTERM/SIGINT directly, so the persistent loop can shut down gracefully.
CMD ["node", "src/index.js"]
