defmodule TenantExchangeWeb.WebFlowTest do
  use TenantExchangeWeb.ConnCase, async: true

  setup do
    TenantExchange.Seeds.insert!()
    :ok
  end

  test "home page is a DuckExchange landing portal", %{conn: conn} do
    conn = get(conn, "/")

    body = html_response(conn, 200)
    assert body =~ "DuckExchange"
    assert body =~ "Sign up"
    assert body =~ "Sign in"
    assert body =~ "Inbox"
    assert body =~ "/inbox"
    refute body =~ "duck{"
  end

  test "login page holds the sign-in form", %{conn: conn} do
    conn = get(conn, "/login")

    body = html_response(conn, 200)
    assert body =~ "DuckExchange"
    assert body =~ "Sign in to review deliveries"
    assert body =~ "Create analyst account"
  end

  test "registration accepts a strong password and login redirects to otp", %{conn: conn} do
    email = unique_email()
    password = strong_password()

    conn =
      post(conn, "/register", %{
        "name" => "Acme Analyst",
        "email" => email,
        "password" => password
      })

    assert redirected_to(conn) == "/login"

    conn = post(recycle(conn), "/login", %{"email" => email, "password" => password})
    assert redirected_to(conn) == "/otp"
    assert Map.has_key?(conn.resp_cookies, "tv_session")
    # Manual-reuse teaching: cookie is scoped to /otp so browsers do not auto-send it to /inbox.
    set_cookie = List.first(get_resp_header(conn, "set-cookie"))
    assert set_cookie =~ "tv_session="
    assert String.downcase(set_cookie) =~ "path=/otp"
  end

  test "otp page has no clickable jump to inbox or docs", %{conn: conn} do
    conn = register_and_login(conn)
    conn = get(recycle(conn), "/otp")

    body = html_response(conn, 200)
    assert body =~ "Enter your one-time code"
    refute body =~ "/inbox"
    refute body =~ "/notifications"
    refute body =~ "/docs/"
  end

  test "otp form is rate limited and does not unlock by brute force", %{conn: conn} do
    conn = register_and_login(conn)

    Enum.each(1..4, fn attempt ->
      conn = post(recycle(conn), "/otp", %{"otp" => Integer.to_string(attempt)})
      assert html_response(conn, 401) =~ "invalid or expired verification code"
    end)

    conn = post(recycle(conn), "/otp", %{"otp" => "555555"})
    assert html_response(conn, 429) =~ "too many verification attempts"
  end

  test "inbox requires a tenant session", %{conn: conn} do
    conn = get(conn, "/inbox")

    body = response(conn, 403)
    assert body =~ "Access denied"
    assert body =~ "403 Forbidden"
  end

  test "notifications alias also requires a tenant session", %{conn: conn} do
    conn = get(conn, "/notifications")

    body = response(conn, 403)
    assert body =~ "Access denied"
    assert body =~ "403 Forbidden"
  end

  test "exchange lookup without session is forbidden", %{conn: conn} do
    conn = get(conn, "/exchange/lookup", %{"q" => "IR-4472"})

    body = response(conn, 403)
    assert body =~ "Access denied"
  end

  test "otp without session is forbidden", %{conn: conn} do
    conn = get(conn, "/otp")

    body = response(conn, 403)
    assert body =~ "Access denied"
  end

  test "unknown root paths return a clean not found response", %{conn: conn} do
    conn = get(conn, "/Dockerfile")

    assert response(conn, 404) =~ "not found"
  end

  test "logged in tenant can see its inbox document ids", %{conn: conn} do
    conn = register_and_login(conn)
    conn = get(recycle(conn), "/inbox")

    body = html_response(conn, 200)
    assert body =~ "DuckExchange Inbox"
    assert body =~ "Review queue for Acme Corp"
    assert body =~ "External delivery queue"
    assert body =~ "IR-4472"
    assert body =~ "/exchange/lookup"
    assert body =~ "/api/v1/tenants/acme-corp/documents/"
    # Docs link is hidden: no clickable href, only an unused JS constant.
    assert body =~ "DOCS_PATH"
    assert body =~ "/docs/"
    refute body =~ "href=\"/docs/"
    refute body =~ "/api/v1/tenants/initech-inc/documents/"
    refute body =~ "Flag:"
  end

  test "exchange lookup is a blind delivery oracle", %{conn: conn} do
    conn = register_and_login(conn)
    conn = get(recycle(conn), "/exchange/lookup", %{"q" => "IR-4472"})

    body = html_response(conn, 200)
    assert body =~ "Pending tenant verification"
    refute body =~ "duck{"
    refute body =~ ~r/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/
  end

  test "exchange lookup starts blank before a reference is submitted", %{conn: conn} do
    conn = register_and_login(conn)
    conn = get(recycle(conn), "/exchange/lookup")

    body = html_response(conn, 200)
    assert body =~ ~s(placeholder="Enter delivery reference")
    refute body =~ "IR-4472"
    refute body =~ "Pending tenant verification"
    refute body =~ "No routed object found"
  end

  test "exchange lookup does not expose the runtime flag as a substring oracle", %{conn: conn} do
    conn = register_and_login(conn)
    conn = get(recycle(conn), "/exchange/lookup", %{"q" => "duck{"})

    body = html_response(conn, 200)
    assert body =~ "No routed object found"
    refute body =~ "Pending tenant verification"
    refute body =~ "Flag:"
  end

  defp register_and_login(conn) do
    email = unique_email()
    password = strong_password()

    conn =
      post(conn, "/register", %{
        "name" => "Acme Analyst",
        "email" => email,
        "password" => password
      })

    post(recycle(conn), "/login", %{"email" => email, "password" => password})
  end

  defp unique_email do
    "analyst+" <> Integer.to_string(System.unique_integer([:positive])) <> "@example.test"
  end

  defp strong_password do
    Enum.join(["A", "a", "1", "!", "xxxx", Integer.to_string(System.unique_integer([:positive]))])
  end
end
