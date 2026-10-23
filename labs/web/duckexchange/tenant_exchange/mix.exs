defmodule TenantExchange.MixProject do
  use Mix.Project

  def project do
    [
      app: :tenant_exchange,
      version: "0.1.0",
      elixir: "~> 1.15",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps()
    ]
  end

  def application do
    [
      mod: {TenantExchange.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "~> 1.7.0"},
      {:phoenix_ecto, "~> 4.5"},
      {:ecto_sql, "~> 3.11"},
      {:postgrex, ">= 0.0.0"},
      {:jason, "~> 1.4"},
      {:plug_cowboy, "~> 2.7"},
      {:phoenix_html, "~> 4.0"},
      {:dns_cluster, "~> 0.1"},
      {:grpc, "0.11.0"},
      {:protobuf, "~> 0.14"}
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.create", "ecto.migrate"],
      "ecto.reset": ["ecto.drop", "ecto.setup"],
      test: ["ecto.create --quiet", "ecto.migrate --quiet", "test"]
    ]
  end
end
