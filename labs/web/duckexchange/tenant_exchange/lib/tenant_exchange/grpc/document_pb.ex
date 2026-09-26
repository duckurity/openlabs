defmodule Tenantexchange.GetDocumentRequest do
  @moduledoc false
  use Protobuf, protoc_gen_elixir_version: "0.14.1", syntax: :proto3

  field :tenant_id, 1, type: :string, json_name: "tenantId"
  field :doc_id, 2, type: :string, json_name: "docId"
end

defmodule Tenantexchange.DocumentReply do
  @moduledoc false
  use Protobuf, protoc_gen_elixir_version: "0.14.1", syntax: :proto3

  field :tenant_id, 1, type: :string, json_name: "tenantId"
  field :doc_id, 2, type: :string, json_name: "docId"
  field :title, 3, type: :string
  field :body, 4, type: :string
  field :classification, 5, type: :string
end

defmodule Tenantexchange.Documents.Service do
  @moduledoc false
  use GRPC.Service, name: "tenantexchange.Documents", protoc_gen_elixir_version: "0.14.1"

  rpc :GetDocument, Tenantexchange.GetDocumentRequest, Tenantexchange.DocumentReply, %{
    http: %{
      type: Google.Api.PbExtension,
      value: %Google.Api.HttpRule{
        selector: "",
        body: "",
        additional_bindings: [],
        response_body: "",
        pattern: {:get, "/api/v1/tenants/{tenant_id}/documents/{doc_id}"},
        __unknown_fields__: []
      }
    }
  }
end

defmodule Tenantexchange.Documents.Stub do
  @moduledoc false
  use GRPC.Stub, service: Tenantexchange.Documents.Service
end
