defmodule TenantExchange.Application do
  use Application

  @impl true
  def start(_type, _args) do
    lookup_repo = Application.get_env(:tenant_exchange, :lookup_repo, TenantExchange.LookupRepo)

    repo_children =
      [TenantExchange.Repo] ++
        if lookup_repo == TenantExchange.Repo do
          []
        else
          [lookup_repo]
        end

    children = [
      repo_children,
      {Phoenix.PubSub, name: TenantExchange.PubSub},
      TenantExchangeWeb.Endpoint,
      grpc_child_spec()
    ]
    |> List.flatten()

    opts = [strategy: :one_for_one, name: TenantExchange.Supervisor]

    with {:ok, pid} <- Supervisor.start_link(children, opts) do
      TenantExchange.Seeds.ensure!()
      {:ok, pid}
    end
  end

  @impl true
  def config_change(changed, _new, removed) do
    TenantExchangeWeb.Endpoint.config_change(changed, removed)
    :ok
  end

  defp grpc_child_spec do
    GRPC.Server.Supervisor.child_spec(
      endpoint: TenantExchange.Grpc.Endpoint,
      port: Application.fetch_env!(:tenant_exchange, :grpc_port),
      start_server: true,
      adapter_opts: [
        ip: {0, 0, 0, 0},
        middlewares: [
          GRPC.Server.Adapters.Cowboy.Router,
          TenantExchange.Grpc.TenantGuard,
          :cowboy_handler
        ]
      ]
    )
  end
end
