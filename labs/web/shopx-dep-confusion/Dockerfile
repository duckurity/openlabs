# ---- Stage 1: builder ----
FROM node:20.17.0-bookworm-slim AS builder

WORKDIR /build

COPY web-app/package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY web-app/server.js ./
COPY web-app/public ./public

# ---- Stage 2: runtime ----
FROM node:20.17.0-bookworm-slim AS runtime

WORKDIR /srv

COPY --from=builder --chown=node:node /build/node_modules ./node_modules
COPY --from=builder --chown=node:node /build/server.js ./server.js
COPY --from=builder --chown=node:node /build/public ./public
COPY --chown=node:node web-app/package.json ./package.json

USER node

EXPOSE 3000
CMD ["node", "server.js"]
