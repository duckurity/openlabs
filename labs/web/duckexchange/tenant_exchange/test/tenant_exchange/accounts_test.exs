defmodule TenantExchange.AccountsTest do
  use TenantExchange.DataCase, async: true

  alias TenantExchange.Accounts

  setup do
    TenantExchange.Seeds.insert!()
    :ok
  end

  test "registration enforces password complexity" do
    assert {:error, "password must be at least 8 characters"} =
             Accounts.register_user(%{
               "name" => "Acme Analyst",
               "email" => unique_email(),
               "password" => short_password()
             })
  end

  test "registered user login creates a pre-otp trusted session" do
    email = unique_email()
    password = strong_password()

    assert {:ok, user} =
             Accounts.register_user(%{
               "name" => "Acme Analyst",
               "email" => String.upcase(email),
               "password" => password
             })

    assert user.email == email
    assert user.tenant.slug == "acme-corp"

    assert {:ok, {token, session}} = Accounts.authenticate(email, password)
    assert byte_size(token) > 32
    assert session.tenant.slug == "acme-corp"
    assert Accounts.tenant_for_session(token).slug == "acme-corp"
  end

  test "invalid user login is rejected" do
    assert :error = Accounts.authenticate(unique_email(), strong_password())
  end

  test "seeded tenant credentials are not usable for player login" do
    assert :error = Accounts.authenticate("acme", "acme")
  end

  test "otp attempts are rate limited but do not revoke the trusted session" do
    email = unique_email()
    password = strong_password()

    assert {:ok, _user} =
             Accounts.register_user(%{
               "name" => "Acme Analyst",
               "email" => email,
               "password" => password
             })

    assert {:ok, {token, _session}} = Accounts.authenticate(email, password)

    assert {:error, :invalid} = Accounts.verify_otp(token, "000000")
    assert {:error, :invalid} = Accounts.verify_otp(token, "111111")
    assert {:error, :invalid} = Accounts.verify_otp(token, "222222")
    assert {:error, :invalid} = Accounts.verify_otp(token, "333333")
    assert {:error, :rate_limited} = Accounts.verify_otp(token, "444444")
    assert Accounts.tenant_for_session(token).slug == "acme-corp"
  end

  defp unique_email do
    "analyst+" <> Integer.to_string(System.unique_integer([:positive])) <> "@example.test"
  end

  defp strong_password do
    Enum.join(["A", "a", "1", "!", "xxxx", Integer.to_string(System.unique_integer([:positive]))])
  end

  defp short_password, do: Enum.join(["A", "a", "1", "!"])
end
