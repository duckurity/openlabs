import Config

if config_env() == :prod do
  config :tenant_exchange, TenantExchange.Repo,
    username: System.fetch_env!("POSTGRES_USER"),
    password: System.fetch_env!("POSTGRES_PASSWORD"),
    hostname: System.fetch_env!("POSTGRES_HOST"),
    database: System.fetch_env!("POSTGRES_DB"),
    pool_size: String.to_integer(System.get_env("POOL_SIZE", "10"))

  config :tenant_exchange, TenantExchange.LookupRepo,
    username: System.get_env("LOOKUP_DB_USER", "tenant_exchange_lookup"),
    password: System.fetch_env!("LOOKUP_DB_PASSWORD"),
    hostname: System.fetch_env!("POSTGRES_HOST"),
    database: System.fetch_env!("POSTGRES_DB"),
    pool_size: String.to_integer(System.get_env("LOOKUP_POOL_SIZE", "4"))

  config :tenant_exchange, TenantExchangeWeb.Endpoint,
    http: [ip: {0, 0, 0, 0}, port: String.to_integer(System.get_env("PORT", "4000"))],
    secret_key_base: System.fetch_env!("SECRET_KEY_BASE"),
    server: true

  config :tenant_exchange, :grpc_port, String.to_integer(System.get_env("GRPC_PORT", "50051"))
  config :tenant_exchange, :seed_on_start, true
  config :tenant_exchange, :flag_file, System.fetch_env!("FLAG_FILE")
end
