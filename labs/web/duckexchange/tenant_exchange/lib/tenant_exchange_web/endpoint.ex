defmodule TenantExchangeWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :tenant_exchange

  @session_options [
    store: :cookie,
    key: "_tenantexchange_key",
    signing_salt: "tenantexchange",
    same_site: "Lax"
  ]

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]
  plug Plug.Parsers, parsers: [:urlencoded, :json], pass: ["*/*"], json_decoder: Phoenix.json_library()
  plug Plug.MethodOverride
  plug Plug.Head
  plug Plug.Session, @session_options
  plug TenantExchangeWeb.Router
end
