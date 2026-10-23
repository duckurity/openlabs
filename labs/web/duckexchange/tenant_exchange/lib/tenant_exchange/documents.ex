defmodule TenantExchange.Documents do
  import Ecto.Query

  alias TenantExchange.Accounts.Tenant
  alias TenantExchange.Documents.Document
  alias TenantExchange.LookupRepo
  alias TenantExchange.Repo

  def list_for_tenant_slug(slug) do
    Document
    |> join(:inner, [d], t in assoc(d, :tenant))
    |> where([d, t], t.slug == ^slug)
    |> order_by([d], asc: d.inserted_at)
    |> select([d], d)
    |> Repo.all()
  end

  def get_for_tenant_slug(slug, doc_id) do
    Document
    |> join(:inner, [d], t in assoc(d, :tenant))
    |> where([d, t], t.slug == ^slug and d.id == ^doc_id)
    |> select([d], d)
    |> Repo.one()
  end

  def external_delivery_probe(ref) when is_binary(ref) do
    if String.trim(ref) == "" do
      :not_matched
    else
      unsafe_external_delivery_probe(ref)
    end
  end

  defp unsafe_external_delivery_probe(ref) do
    sql = """
    SELECT doc_id
    FROM (
      SELECT doc_id
      FROM challenge_lookup.delivery_index
      ORDER BY priority ASC
      LIMIT 1
    ) AS first_delivery
    WHERE 'IR-4472' ILIKE '%#{ref}%'
    LIMIT 1
    """

    lookup_repo = Application.get_env(:tenant_exchange, :lookup_repo, LookupRepo)

    case lookup_repo.query(sql, []) do
      {:ok, %{num_rows: rows}} when rows > 0 -> :matched
      _ -> :not_matched
    end
  end

  def public_seed_docs do
    Repo.all(from d in Document, order_by: [asc: d.title])
  end

  def get_tenant_by_slug(slug), do: Repo.get_by(Tenant, slug: slug)
end
