defmodule TenantExchange.Documents.Document do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "documents" do
    field :title, :string
    field :body, :string
    field :classification, :string

    belongs_to :tenant, TenantExchange.Accounts.Tenant

    timestamps(type: :utc_datetime)
  end

  def changeset(document, attrs) do
    document
    |> cast(attrs, [:title, :body, :classification, :tenant_id])
    |> validate_required([:title, :body, :classification, :tenant_id])
    |> foreign_key_constraint(:tenant_id)
  end
end
