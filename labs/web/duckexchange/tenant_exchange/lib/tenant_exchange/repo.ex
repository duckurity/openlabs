defmodule TenantExchange.Repo do
  use Ecto.Repo,
    otp_app: :tenant_exchange,
    adapter: Ecto.Adapters.Postgres
end
