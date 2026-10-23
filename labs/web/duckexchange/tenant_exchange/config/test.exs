import Config

config :tenant_exchange, TenantExchange.Repo,
  username: System.get_env("POSTGRES_USER", "tenantexchange"),
  password: System.get_env("POSTGRES_PASSWORD", "tenantexchange"),
  hostname: System.get_env("POSTGRES_HOST", "localhost"),
  database: System.get_env("POSTGRES_TEST_DB", "tenantexchange_test"),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 10

config :tenant_exchange, :lookup_repo, TenantExchange.Repo

config :tenant_exchange, TenantExchangeWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: String.duplicate("b", 64),
  server: false

config :tenant_exchange, :grpc_port, 0
config :tenant_exchange, :seed_on_start, false
config :tenant_exchange, :flag, "TEST_FLAG_SENTINEL"
config :logger, level: :warning
