defmodule TenantExchange.Grpc.TenantGuard do
  @behaviour :cowboy_middleware

  alias TenantExchange.Accounts

  @impl true
  def execute(req, env) do
    path_tenant =
      req
      |> :cowboy_req.bindings()
      |> then(fn bindings -> Map.get(bindings, :tenant_id) || Map.get(bindings, "tenant_id") end)

    session_cookie = Accounts.session_cookie()

    session_tenant =
      req
      |> :cowboy_req.parse_cookies()
      |> Enum.find_value(fn
        {^session_cookie, token} -> Accounts.tenant_for_session(token)
        _ -> nil
      end)

    cond do
      is_nil(session_tenant) ->
        {:stop, reply(req, 401, %{error: "sign in required"})}

      session_tenant.slug != path_tenant ->
        {:stop, reply(req, 403, %{error: "tenant denied"})}

      true ->
        {:ok, req, env}
    end
  end

  defp reply(req, status, body) do
    :cowboy_req.reply(
      status,
      %{"content-type" => "application/json"},
      Jason.encode!(body),
      req
    )
  end
end
