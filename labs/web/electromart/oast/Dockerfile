# ---------- ElectroMart OAST callback service ----------
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

# This marker changes on every image build. Compose builds OAST with
# no_cache enabled, so `docker compose up -d --build` always creates a new
# image and recreates the container. The interaction store is in-memory, so a
# fresh container means a clean dashboard.
RUN printf '%s-%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(cat /proc/sys/kernel/random/uuid)" > /app/build-id

# Dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

COPY --chown=node:node src ./src

EXPOSE 4000

# Unprivileged runtime user; no shell wrapper so Docker can signal Node directly.
USER node

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||4000)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "src/server.js"]
