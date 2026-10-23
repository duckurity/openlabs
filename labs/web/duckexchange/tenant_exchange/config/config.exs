import Config

config :tenant_exchange,
  ecto_repos: [TenantExchange.Repo],
  generators: [timestamp_type: :utc_datetime]

config :tenant_exchange, TenantExchangeWeb.Endpoint,
  url: [host: "localhost"],
  render_errors: [
    formats: [html: TenantExchangeWeb.ErrorHTML, json: TenantExchangeWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: TenantExchange.PubSub,
  live_view: [signing_salt: "tenantexchange"]

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"
