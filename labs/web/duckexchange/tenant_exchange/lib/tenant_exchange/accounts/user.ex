defmodule TenantExchange.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "users" do
    field :name, :string
    field :email, :string
    field :password_hash, :string

    belongs_to :tenant, TenantExchange.Accounts.Tenant

    timestamps(type: :utc_datetime)
  end

  def changeset(user, attrs) do
    user
    |> cast(attrs, [:tenant_id, :name, :email, :password_hash])
    |> validate_required([:tenant_id, :name, :email, :password_hash])
    |> validate_format(:email, ~r/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
    |> update_change(:email, &String.downcase/1)
    |> foreign_key_constraint(:tenant_id)
    |> unique_constraint(:email)
  end
end
