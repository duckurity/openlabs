defmodule TenantExchangeWeb.ConnCase do
  use ExUnit.CaseTemplate

  using do
    quote do
      @endpoint TenantExchangeWeb.Endpoint
      use Phoenix.ConnTest

    end
  end

  setup tags do
    TenantExchange.DataCase.setup_sandbox(tags)
    {:ok, conn: Phoenix.ConnTest.build_conn()}
  end

end
