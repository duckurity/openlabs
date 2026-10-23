import Config

config :tenant_exchange, TenantExchange.Repo,
  username: System.get_env("POSTGRES_USER", "tenantexchange"),
  password: System.get_env("POSTGRES_PASSWORD", "tenantexchange"),
  hostname: System.get_env("POSTGRES_HOST", "localhost"),
  database: System.get_env("POSTGRES_DB", "tenantexchange_dev"),
  stacktrace: true,
  show_sensitive_data_on_connection_error: false,
  pool_size: 10

config :tenant_exchange, TenantExchange.LookupRepo,
  username: System.get_env("LOOKUP_DB_USER", "tenant_exchange_lookup"),
  password: System.get_env("LOOKUP_DB_PASSWORD", "tenant_exchange_lookup_password"),
  hostname: System.get_env("POSTGRES_HOST", "localhost"),
  database: System.get_env("POSTGRES_DB", "tenantexchange_dev"),
  pool_size: 4

config :tenant_exchange, TenantExchangeWeb.Endpoint,
  http: [ip: {0, 0, 0, 0}, port: String.to_integer(System.get_env("PORT", "4000"))],
  check_origin: false,
  code_reloader: false,
  debug_errors: false,
  secret_key_base: System.get_env("SECRET_KEY_BASE", String.duplicate("a", 64)),
  server: true

config :tenant_exchange, :grpc_port, String.to_integer(System.get_env("GRPC_PORT", "50051"))
config :tenant_exchange, :seed_on_start, true
config :tenant_exchange, :flag_file, System.get_env("FLAG_FILE", "/run/secrets/challenge_flag")
