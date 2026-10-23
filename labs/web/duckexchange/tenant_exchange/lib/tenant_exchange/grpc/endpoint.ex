defmodule TenantExchange.Grpc.Endpoint do
  use GRPC.Endpoint

  run TenantExchange.Grpc.DocumentServer
end
