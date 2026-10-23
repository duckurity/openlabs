FROM node:20.19.5-alpine3.21

WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY app/package.json app/package-lock.json ./
RUN npm ci --omit=dev

COPY --chown=appuser:appgroup app/server.js ./
COPY --chown=appuser:appgroup app/src ./src

USER appuser

EXPOSE 3000 50051

CMD ["node", "server.js"]