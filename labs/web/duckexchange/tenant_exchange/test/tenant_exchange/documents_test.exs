defmodule TenantExchange.DocumentsTest do
  use TenantExchange.DataCase, async: true

  alias TenantExchange.Documents
  alias TenantExchange.Grpc.DocumentServer
  alias Tenantexchange.GetDocumentRequest

  setup do
    TenantExchange.Seeds.insert!()
    :ok
  end

  test "seeded acme notifications do not include the restricted flag document" do
    docs = Documents.list_for_tenant_slug("acme-corp")

    refute Enum.any?(docs, &String.contains?(&1.body, "TEST_FLAG_SENTINEL"))
    assert Enum.count(docs) >= 3
  end

  test "server-side document lookup keeps the runtime flag out of stored rows" do
    flag_doc = restricted_flag_doc()

    assert Documents.get_for_tenant_slug("initech-inc", flag_doc.id).body =~ "Incident IR-4472"
    refute Documents.get_for_tenant_slug("initech-inc", flag_doc.id).body =~ "TEST_FLAG_SENTINEL"
    assert is_nil(Documents.get_for_tenant_slug("acme-corp", flag_doc.id))
  end

  test "grpc document response includes the runtime flag for the restricted packet" do
    flag_doc = restricted_flag_doc()

    reply =
      DocumentServer.get_document(
        %GetDocumentRequest{tenant_id: "initech-inc", doc_id: flag_doc.id},
        nil
      )

    assert reply.body =~ "Incident IR-4472"
    assert reply.body =~ "TEST_FLAG_SENTINEL"
  end

  test "external delivery probe can be used as a boolean UUID oracle" do
    flag_doc = restricted_flag_doc()

    first_char = String.first(flag_doc.id)
    wrong_char = if first_char == "a", do: "b", else: "a"

    assert Documents.external_delivery_probe("IR-4472") == :matched

    assert Documents.external_delivery_probe(
             "missing%' OR substring(doc_id::text,1,1) = '#{first_char}'--"
           ) == :matched

    assert Documents.external_delivery_probe(
             "missing%' OR substring(doc_id::text,1,1) = '#{wrong_char}'--"
           ) == :not_matched
  end

  test "external delivery probe cannot recover the runtime flag directly" do
    assert Documents.external_delivery_probe("TEST_FLAG") == :not_matched
    assert Documents.external_delivery_probe("test_flag") == :not_matched

    assert Documents.external_delivery_probe(
             "missing%' OR substring(body,1,5) = 'TEST_'--"
           ) == :not_matched
  end

  defp restricted_flag_doc do
    "initech-inc"
    |> Documents.list_for_tenant_slug()
    |> Enum.find(&(&1.title == "Incident IR-4472 Escalation"))
  end
end
