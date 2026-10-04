defmodule TenantExchange.Repo.Migrations.CreateTenantExchangeTables do
  use Ecto.Migration

  def change do
    create table(:tenants, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :slug, :text, null: false
      add :name, :text, null: false
      add :login, :text, null: false
      add :password_hash, :text, null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:tenants, [:slug])
    create unique_index(:tenants, [:login])

    create table(:users, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :tenant_id, references(:tenants, type: :uuid, on_delete: :delete_all), null: false
      add :name, :text, null: false
      add :email, :text, null: false
      add :password_hash, :text, null: false

      timestamps(type: :utc_datetime)
    end

    create index(:users, [:tenant_id])
    create unique_index(:users, [:email])

    create table(:documents, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :tenant_id, references(:tenants, type: :uuid, on_delete: :delete_all), null: false
      add :title, :text, null: false
      add :body, :text, null: false
      add :classification, :text, null: false

      timestamps(type: :utc_datetime)
    end

    create index(:documents, [:tenant_id])
    create unique_index(:documents, [:tenant_id, :title])

    create table(:sessions, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :tenant_id, references(:tenants, type: :uuid, on_delete: :delete_all), null: false
      add :token_hash, :bytea, null: false
      add :expires_at, :utc_datetime, null: false
      add :otp_attempts, :integer, null: false, default: 0
      add :otp_locked_until, :utc_datetime

      timestamps(type: :utc_datetime, updated_at: false)
    end

    create index(:sessions, [:tenant_id])
    create unique_index(:sessions, [:token_hash])
  end
end
