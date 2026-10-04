defmodule TenantExchange.Grpc.TranscodeTest do
  use ExUnit.Case, async: true

  test "grpc 0.11 transcode maps query fields over path fields" do
    rule = %Google.Api.HttpRule{body: ""}
    path_bindings = %{"tenant_id" => "acme-corp", "doc_id" => "doc-1"}
    query_string = "tenant_id=initech-inc"

    assert {:ok, request} =
             GRPC.Server.Transcode.map_request(
               rule,
               %{},
               path_bindings,
               query_string,
               Tenantexchange.GetDocumentRequest
             )

    assert request.tenant_id == "initech-inc"
    assert request.doc_id == "doc-1"
  end
end
