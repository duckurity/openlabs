FROM node:20.17.0-bookworm-slim

WORKDIR /srv

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY server.js .

EXPOSE 5000
CMD ["node", "server.js"]
