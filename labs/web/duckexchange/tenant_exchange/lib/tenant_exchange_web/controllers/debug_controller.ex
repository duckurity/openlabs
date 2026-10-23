defmodule TenantExchangeWeb.DebugController do
  use TenantExchangeWeb, :controller

  alias TenantExchange.Accounts

  def show(conn, %{"token" => "route-check"}) do
    conn = fetch_cookies(conn)
    cookie = Map.get(conn.cookies, Accounts.session_cookie())
    tenant = Accounts.tenant_for_session(cookie)

    json(conn, %{
      request_id: List.first(get_resp_header(conn, "x-request-id")),
      authenticated_tenant: tenant && tenant.slug,
      grpc_document_route: "/api/v1/tenants/:tenant_id/documents/:doc_id",
      grpc_port: Application.fetch_env!(:tenant_exchange, :grpc_port),
      note: "debug route exposes request context only"
    })
  end

  def show(conn, _params) do
    conn
    |> put_status(:not_found)
    |> json(%{error: "not found"})
  end
end
