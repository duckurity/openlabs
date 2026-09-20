defmodule TenantExchangeWeb.SessionController do
  use TenantExchangeWeb, :controller

  alias TenantExchange.Accounts

  def register(conn, params) do
    case Accounts.register_user(params) do
      {:ok, _user} ->
        conn
        |> redirect(to: ~p"/login")

      {:error, reason} ->
        conn
        |> put_status(:unprocessable_entity)
        |> html(TenantExchangeWeb.PageController.register_page(reason, params))
    end
  end

  def create(conn, %{"email" => email, "password" => password}) do
    case Accounts.authenticate(email, password) do
      {:ok, {token, _session}} ->
        conn
        |> put_resp_cookie(Accounts.session_cookie(), token,
          http_only: true,
          same_site: "Lax",
          max_age: 8 * 60 * 60,
          path: "/otp"
        )
        |> redirect(to: ~p"/otp")

      :error ->
        conn
        |> put_status(:unauthorized)
        |> html(TenantExchangeWeb.PageController.login_page("invalid email or password"))
    end
  end

  def verify_otp(conn, %{"otp" => otp}) do
    conn = fetch_cookies(conn)
    token = Map.get(conn.cookies, Accounts.session_cookie())

    case Accounts.verify_otp(token, otp) do
      {:error, :rate_limited} ->
        conn
        |> put_status(:too_many_requests)
        |> html(TenantExchangeWeb.PageController.otp_page("too many verification attempts; request a new code later"))

      {:error, :unauthorized} ->
        conn
        |> put_status(:forbidden)
        |> html(TenantExchangeWeb.PageController.forbidden_page("/otp"))

      {:error, :invalid} ->
        conn
        |> put_status(:unauthorized)
        |> html(TenantExchangeWeb.PageController.otp_page("invalid or expired verification code"))
    end
  end

  def delete(conn, _params) do
    conn = fetch_cookies(conn)

    conn.cookies
    |> Map.get(Accounts.session_cookie())
    |> then(fn
      nil -> :ok
      token -> Accounts.delete_session(token)
    end)

    conn
    |> delete_resp_cookie(Accounts.session_cookie(), path: "/otp")
    |> redirect(to: ~p"/")
  end
end
