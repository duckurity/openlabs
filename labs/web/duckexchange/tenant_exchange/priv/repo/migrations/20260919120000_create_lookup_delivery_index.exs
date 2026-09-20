defmodule TenantExchange.Repo.Migrations.CreateLookupDeliveryIndex do
  use Ecto.Migration

  @lookup_role "tenant_exchange_lookup"

  def up do
    execute("CREATE SCHEMA IF NOT EXISTS challenge_lookup")

    execute("""
    CREATE TABLE IF NOT EXISTS challenge_lookup.delivery_index (
      doc_id uuid PRIMARY KEY,
      priority integer NOT NULL DEFAULT 100
    )
    """)

    if Application.get_env(:tenant_exchange, :lookup_repo, TenantExchange.LookupRepo) !=
         TenantExchange.Repo do
      password =
        System.get_env("LOOKUP_DB_PASSWORD", "tenant_exchange_lookup_password")
        |> String.replace("'", "''")

      execute("""
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '#{@lookup_role}') THEN
          CREATE ROLE #{@lookup_role}
            LOGIN PASSWORD '#{password}'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
        ELSE
          ALTER ROLE #{@lookup_role}
            LOGIN PASSWORD '#{password}'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
        END IF;
      END
      $$;
      """)

      execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM #{@lookup_role}")
      execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM #{@lookup_role}")
      execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM #{@lookup_role}")
      execute("GRANT USAGE ON SCHEMA challenge_lookup TO #{@lookup_role}")
      execute("GRANT SELECT ON challenge_lookup.delivery_index TO #{@lookup_role}")
      execute("ALTER ROLE #{@lookup_role} SET search_path = challenge_lookup, pg_catalog")
    end
  end

  def down do
    execute("DROP TABLE IF EXISTS challenge_lookup.delivery_index")
    execute("DROP SCHEMA IF EXISTS challenge_lookup")

    if Application.get_env(:tenant_exchange, :lookup_repo, TenantExchange.LookupRepo) !=
         TenantExchange.Repo do
      execute("DROP ROLE IF EXISTS #{@lookup_role}")
    end
  end
end
