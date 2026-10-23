defmodule TenantExchange.Repo.Migrations.AddDeliveryPriority do
  use Ecto.Migration

  def up do
    execute("""
    ALTER TABLE challenge_lookup.delivery_index
    ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 100
    """)

    execute("""
    UPDATE challenge_lookup.delivery_index AS i
    SET priority = 0
    FROM public.documents AS d
    JOIN public.tenants AS t ON t.id = d.tenant_id
    WHERE i.doc_id = d.id
      AND t.slug = 'initech-inc'
      AND d.title = 'Incident IR-4472 Escalation'
    """)
  end

  def down do
    execute("""
    ALTER TABLE challenge_lookup.delivery_index
    DROP COLUMN IF EXISTS priority
    """)
  end
end
