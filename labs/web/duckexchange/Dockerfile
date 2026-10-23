FROM elixir:1.18-alpine

RUN apk add --no-cache build-base git postgresql-client

WORKDIR /app

ENV MIX_ENV=dev
ENV PORT=4001
ENV GRPC_PORT=50051

COPY tenant_exchange/mix.exs tenant_exchange/mix.lock* ./
RUN mix local.hex --force && mix local.rebar --force && mix deps.get

COPY tenant_exchange/ ./
RUN chmod +x /app/entrypoint.sh && mix deps.compile && mix compile \
    && addgroup -S app \
    && adduser -S -G app app \
    && chown -R app:app /app

EXPOSE 4001 50051

USER app

CMD ["/app/entrypoint.sh"]
