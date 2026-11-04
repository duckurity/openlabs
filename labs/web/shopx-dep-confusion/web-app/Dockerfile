FROM node:20.17.0-bookworm-slim

WORKDIR /srv

COPY package.json package-lock.json* ./
RUN npm install --omit=dev --no-audit --no-fund

COPY . .

EXPOSE 3000
CMD ["node", "server.js"]
