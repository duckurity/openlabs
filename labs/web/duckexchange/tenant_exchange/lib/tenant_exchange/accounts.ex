defmodule TenantExchange.Accounts do
  import Ecto.Query

  alias TenantExchange.Accounts.{Session, Tenant, User}
  alias TenantExchange.Repo

  @session_cookie "tv_session"
  @otp_attempt_limit 5
  @otp_lock_seconds 30 * 60

  def session_cookie, do: @session_cookie

  def register_user(attrs) do
    name = attrs |> Map.get("name", "") |> String.trim()
    email = attrs |> Map.get("email", "") |> normalize_email()
    password = Map.get(attrs, "password", "")

    with :ok <- validate_password(password),
         %Tenant{} = tenant <- Repo.get_by(Tenant, slug: "acme-corp") do
      %User{}
      |> User.changeset(%{
        tenant_id: tenant.id,
        name: name,
        email: email,
        password_hash: password_hash(password)
      })
      |> Repo.insert()
      |> case do
        {:ok, user} -> {:ok, Repo.preload(user, :tenant)}
        {:error, changeset} -> {:error, user_error(changeset)}
      end
    else
      {:error, reason} -> {:error, reason}
      _ -> {:error, "registration is temporarily unavailable"}
    end
  end

  def authenticate(email, password) do
    with %User{} = user <- Repo.get_by(User, email: normalize_email(email)) |> Repo.preload(:tenant),
         true <- password_hash(password) == user.password_hash do
      {:ok, create_session!(user.tenant)}
    else
      _ -> :error
    end
  end

  def create_session!(%Tenant{} = tenant) do
    token = :crypto.strong_rand_bytes(32) |> Base.url_encode64(padding: false)
    token_hash = hash_token(token)
    expires_at = DateTime.utc_now() |> DateTime.add(8, :hour) |> DateTime.truncate(:second)

    session =
      %Session{}
      |> Session.changeset(%{tenant_id: tenant.id, token_hash: token_hash, expires_at: expires_at})
      |> Repo.insert!()
      |> Repo.preload(:tenant)

    {token, session}
  end

  def verify_otp(token, _code) when is_binary(token) do
    now = DateTime.utc_now() |> DateTime.truncate(:second)

    with %Session{} = session <- session_for_token(token) do
      cond do
        not is_nil(session.otp_locked_until) and DateTime.compare(session.otp_locked_until, now) == :gt ->
          {:error, :rate_limited}

        session.otp_attempts + 1 >= @otp_attempt_limit ->
          lock_until = DateTime.add(now, @otp_lock_seconds, :second)

          session
          |> Session.changeset(%{otp_attempts: session.otp_attempts + 1, otp_locked_until: lock_until})
          |> Repo.update!()

          {:error, :rate_limited}

        true ->
          session
          |> Session.changeset(%{otp_attempts: session.otp_attempts + 1})
          |> Repo.update!()

          {:error, :invalid}
      end
    else
      _ -> {:error, :unauthorized}
    end
  end

  def tenant_for_session(nil), do: nil
  def tenant_for_session(""), do: nil

  def tenant_for_session(token) when is_binary(token) do
    token
    |> session_for_token()
    |> case do
      %Session{tenant: tenant} -> tenant
      _ -> nil
    end
  end

  def delete_session(token) when is_binary(token) do
    token_hash = hash_token(token)

    Session
    |> where([s], s.token_hash == ^token_hash)
    |> Repo.delete_all()
  end

  def password_hash(password) when is_binary(password) do
    :crypto.hash(:sha256, "tenant-exchange-demo:" <> password) |> Base.encode16(case: :lower)
  end

  defp session_for_token(token) when is_binary(token) do
    now = DateTime.utc_now() |> DateTime.truncate(:second)
    token_hash = hash_token(token)

    Session
    |> where([s], s.token_hash == ^token_hash and s.expires_at > ^now)
    |> join(:inner, [s], t in assoc(s, :tenant))
    |> preload([s, t], tenant: t)
    |> Repo.one()
  end

  defp validate_password(password) when is_binary(password) do
    cond do
      String.length(password) < 8 -> {:error, "password must be at least 8 characters"}
      not Regex.match?(~r/[a-z]/, password) -> {:error, "password must include a lowercase letter"}
      not Regex.match?(~r/[A-Z]/, password) -> {:error, "password must include an uppercase letter"}
      not Regex.match?(~r/[0-9]/, password) -> {:error, "password must include a number"}
      not Regex.match?(~r/[^A-Za-z0-9]/, password) -> {:error, "password must include a special character"}
      true -> :ok
    end
  end

  defp validate_password(_), do: {:error, "password is required"}

  defp user_error(changeset) do
    cond do
      Keyword.has_key?(changeset.errors, :email) -> "email is invalid or already registered"
      Keyword.has_key?(changeset.errors, :name) -> "name is required"
      true -> "registration failed"
    end
  end

  defp normalize_email(email) when is_binary(email), do: email |> String.trim() |> String.downcase()
  defp normalize_email(_), do: ""

  defp hash_token(token), do: :crypto.hash(:sha256, token)
end
