defmodule TenantExchange.Accounts.Session do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "sessions" do
    field :token_hash, :binary
    field :expires_at, :utc_datetime
    field :otp_attempts, :integer, default: 0
    field :otp_locked_until, :utc_datetime

    belongs_to :tenant, TenantExchange.Accounts.Tenant

    timestamps(type: :utc_datetime, updated_at: false)
  end

  def changeset(session, attrs) do
    session
    |> cast(attrs, [:token_hash, :tenant_id, :expires_at, :otp_attempts, :otp_locked_until])
    |> validate_required([:token_hash, :tenant_id, :expires_at])
    |> foreign_key_constraint(:tenant_id)
  end
end
