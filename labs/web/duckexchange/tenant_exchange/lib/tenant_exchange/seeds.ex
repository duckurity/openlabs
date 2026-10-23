defmodule TenantExchange.Seeds do
  alias TenantExchange.Accounts
  alias TenantExchange.Accounts.Tenant
  alias TenantExchange.Documents.Document
  alias TenantExchange.Repo

  def ensure! do
    if Application.get_env(:tenant_exchange, :seed_on_start, false) do
      insert!()
    end
  end

  def insert! do
    acme =
      upsert_tenant(%{
        slug: "acme-corp",
        name: "Acme Corp",
        login: "acme-system",
        password_hash: Accounts.password_hash(:crypto.strong_rand_bytes(48))
      })

    initech =
      upsert_tenant(%{
        slug: "initech-inc",
        name: "Initech Inc",
        login: "initech",
        password_hash: Accounts.password_hash(:crypto.strong_rand_bytes(48))
      })

    acme_soc2 =
      upsert_document(
        acme,
        "SOC2 Evidence - Change Window",
        "Change CAB approved the EU gateway patch for Friday 22:00 UTC. Customer impact: none expected.",
        "internal"
      )

    acme_vendor =
      upsert_document(
        acme,
        "Vendor Access Renewal",
        "Security operations renewed read-only vendor access for the Acme billing connector.",
        "internal"
      )

    acme_legal_hold =
      upsert_document(
        acme,
        "Legal Hold Intake",
        "A cross-tenant legal delivery was routed to review. The attached external object must remain sealed until tenant ownership is verified.",
        "confidential"
      )

    initech_welcome =
      upsert_document(
        initech,
        "Customer Success Welcome",
        "Initech workspace onboarding checklist and support contacts.",
        "internal"
      )

    restricted_doc =
      upsert_document(
        initech,
        "Incident IR-4472 Escalation",
        "Incident IR-4472 final escalation packet. Release is blocked until tenant ownership is verified.",
        "restricted"
      )

    # Keep the restricted IR-4472 document first so the blind oracle remains
    # stable, while the dump contains realistic delivery UUID decoys too.
    for {doc, priority} <- [
          {restricted_doc, 0},
          {acme_soc2, 10},
          {acme_vendor, 20},
          {acme_legal_hold, 30},
          {initech_welcome, 40}
        ] do
      Repo.query!(
        """
        INSERT INTO challenge_lookup.delivery_index (doc_id, priority)
        VALUES ($1, $2)
        ON CONFLICT (doc_id) DO UPDATE SET priority = EXCLUDED.priority
        """,
        [Ecto.UUID.dump!(doc.id), priority]
      )
    end
  end

  defp upsert_tenant(attrs) do
    %Tenant{}
    |> Tenant.changeset(attrs)
    |> Repo.insert!(
      on_conflict: {:replace, [:name, :login, :password_hash, :updated_at]},
      conflict_target: :slug,
      returning: true
    )
  end

  defp upsert_document(tenant, title, body, classification) do
    %Document{}
    |> Document.changeset(%{tenant_id: tenant.id, title: title, body: body, classification: classification})
    |> Repo.insert!(
      on_conflict: {:replace, [:body, :classification, :updated_at]},
      conflict_target: [:tenant_id, :title],
      returning: true
    )
  end
end
