# ---------- ElectroMart application image ----------
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

# Install production dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

# Application code, views, product images. Copy with the runtime user as
# owner so restrictive host directory modes (e.g. 700) cannot block the
# non-root `node` user at runtime.
COPY --chown=node:node src ./src
COPY --chown=node:node views ./views
COPY --chown=node:node public ./public
COPY --chown=node:node devices ./devices

EXPOSE 3000

# Non-root runtime user.
USER node

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "src/server.js"]
