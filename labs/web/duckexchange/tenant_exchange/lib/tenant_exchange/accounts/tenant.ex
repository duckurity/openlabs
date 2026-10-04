defmodule TenantExchange.Accounts.Tenant do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "tenants" do
    field :slug, :string
    field :name, :string
    field :login, :string
    field :password_hash, :string

    has_many :documents, TenantExchange.Documents.Document
    has_many :sessions, TenantExchange.Accounts.Session
    has_many :users, TenantExchange.Accounts.User

    timestamps(type: :utc_datetime)
  end

  def changeset(tenant, attrs) do
    tenant
    |> cast(attrs, [:slug, :name, :login, :password_hash])
    |> validate_required([:slug, :name, :login, :password_hash])
    |> unique_constraint(:slug)
    |> unique_constraint(:login)
  end
end
