defmodule TenantExchange.Grpc.DocumentServer do
  use GRPC.Server,
    service: Tenantexchange.Documents.Service,
    http_transcode: true

  alias TenantExchange.Documents
  alias Tenantexchange.DocumentReply
  alias Tenantexchange.GetDocumentRequest

  def get_document(%GetDocumentRequest{tenant_id: tenant_id, doc_id: doc_id}, _stream) do
    case Documents.get_for_tenant_slug(tenant_id, doc_id) do
      nil ->
        raise GRPC.RPCError, status: :not_found, message: "document not found"

      doc ->
        %DocumentReply{
          tenant_id: tenant_id,
          doc_id: doc.id,
          title: doc.title,
          body: response_body(doc),
          classification: doc.classification
        }
    end
  end

  defp response_body(%{title: "Incident IR-4472 Escalation", classification: "restricted", body: body}) do
    "#{body} Flag: #{runtime_flag()}"
  end

  defp response_body(%{body: body}), do: body

  defp runtime_flag do
    case Application.fetch_env(:tenant_exchange, :flag_file) do
      {:ok, path} ->
        path
        |> File.read!()
        |> String.trim()

      :error ->
        Application.fetch_env!(:tenant_exchange, :flag)
    end
  end
end
