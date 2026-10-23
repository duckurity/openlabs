defmodule TenantExchangeWeb.PageController do
  use TenantExchangeWeb, :controller

  alias TenantExchange.Accounts
  alias TenantExchange.Documents

  def home(conn, _params) do
    html(conn, landing_page())
  end

  def login(conn, _params) do
    html(conn, login_page())
  end

  def register(conn, _params) do
    html(conn, register_page())
  end

  def inbox(conn, params) do
    render_inbox(conn, params)
  end

  def notifications(conn, params) do
    render_inbox(conn, params)
  end

  def landing_page do
    """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DuckExchange</title>
      <style>#{style()}</style>
    </head>
    <body class="login-page">
      <section class="login-shell">
        <div class="brand-panel">
          <div class="brand-mark">DE</div>
          <p class="eyebrow">Duck Exchange</p>
          <h1>Secure delivery exchange for tenant-owned records.</h1>
          <p class="lede">
            Legal and incident response teams use DuckExchange to review sealed delivery objects
            while the gateway enforces tenant boundaries at every route. Each tenant gets an
            isolated review queue, a delivery lookup oracle for routed references, and an
            API for its own documents. External packets stay sealed until ownership is verified.
          </p>
          <div class="system-strip">
            <span>Gateway online</span>
            <span>Document service healthy</span>
            <span>Email verification required</span>
          </div>
          <div class="signal-grid">
            <div><span>What it provides</span><strong>Isolated queues</strong></div>
            <div><span>Lookup</span><strong>Routing oracle</strong></div>
            <div><span>Boundary</span><strong>Path scoped</strong></div>
          </div>
        </div>
        <div class="login-card">
          <nav class="landing-nav" style="display:flex;gap:10px;margin-bottom:24px">
            <a class="ghost-button" href="/register">Sign up</a>
            <a class="ghost-button" href="/login">Sign in</a>
            <a class="ghost-button" href="/inbox">Inbox</a>
          </nav>
          <p class="eyebrow">Analyst workspace</p>
          <h2>Review deliveries in your tenant inbox</h2>
          <p class="muted">Create an analyst account, sign in, then open your inbox to review deliveries.</p>
        </div>
      </section>
    </body>
    </html>
    """
  end

  def otp(conn, _params) do
    case current_tenant(conn) do
      nil ->
        conn
        |> put_status(:forbidden)
        |> html(forbidden_page("/otp"))

      _tenant ->
        html(conn, otp_page())
    end
  end

  def forbidden_page(path \\ "/inbox") do
    """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DuckExchange Access Denied</title>
      <style>#{style()}</style>
    </head>
    <body>
      <main class="lookup-page">
        <section class="lookup-card">
          <p class="eyebrow">Duck Exchange / access control</p>
          <h1>Access denied</h1>
          <p class="muted">You do not have permission to view #{h(path)}. Sign in with an analyst account to continue.</p>
          <div class="lookup-result">
            <span>Policy decision</span>
            <strong>403 Forbidden — tenant verification required</strong>
          </div>
          <p><a href="/login">Sign in</a> · <a href="/">Back to DuckExchange</a></p>
        </section>
      </main>
    </body>
    </html>
    """
  end

  def login_page(error \\ nil) do
    tenant = nil

    """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DuckExchange Sign In</title>
      <style>#{style()}</style>
    </head>
    <body class="login-page">
      <section class="login-shell">
        <div class="brand-panel">
          <div class="brand-mark">DE</div>
          <p class="eyebrow">Duck Exchange</p>
          <h1>Secure delivery exchange for tenant-owned records.</h1>
          <p class="lede">
            Legal and incident response teams use DuckExchange to review sealed delivery objects
            while the gateway enforces tenant boundaries at every route.
          </p>
          <div class="system-strip">
            <span>Gateway online</span>
            <span>Document service healthy</span>
            <span>Email verification required</span>
          </div>
          <div class="signal-grid">
            <div><span>Queue SLA</span><strong>14m</strong></div>
            <div><span>Open Reviews</span><strong>7</strong></div>
            <div><span>Tenant Boundary</span><strong>Path scoped</strong></div>
          </div>
        </div>
        <div class="login-card">
          #{session_panel(tenant)}
          <p class="eyebrow">Analyst workspace</p>
          <h2>Sign in to review deliveries</h2>
          <p class="muted">Use your registered analyst account for this exercise.</p>
          #{alert(error)}
          <form method="post" action="/login">
            <input type="hidden" name="_csrf_token" value="#{Plug.CSRFProtection.get_csrf_token()}">
            <label>Email<input name="email" type="email" autocomplete="username"></label>
            <label>Password<input name="password" type="password" autocomplete="current-password"></label>
            <button type="submit">Continue</button>
          </form>
          <p class="form-footer"><a href="/register">Create analyst account</a></p>
        </div>
      </section>
    </body>
    </html>
    """
  end

  def register_page(error \\ nil, params \\ %{}) do
    """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DuckExchange Registration</title>
      <style>#{style()}</style>
    </head>
    <body class="login-page">
      <section class="login-shell">
        <div class="brand-panel">
          <div class="brand-mark">DE</div>
          <p class="eyebrow">Duck Exchange</p>
          <h1>Provision analyst access for delivery review.</h1>
          <p class="lede">
            New analyst identities are attached to the Acme review workspace after enrollment.
          </p>
          <div class="system-strip">
            <span>Self-service enrollment</span>
            <span>Acme workspace</span>
            <span>Policy audit enabled</span>
          </div>
          <div class="signal-grid">
            <div><span>Password Policy</span><strong>Strict</strong></div>
            <div><span>OTP Channel</span><strong>Email</strong></div>
            <div><span>Review Tenant</span><strong>Acme</strong></div>
          </div>
        </div>
        <div class="login-card">
          <p class="eyebrow">Create account</p>
          <h2>Register analyst identity</h2>
          <p class="muted">Password must include uppercase, lowercase, number, and special character.</p>
          #{alert(error)}
          <form method="post" action="/register">
            <input type="hidden" name="_csrf_token" value="#{Plug.CSRFProtection.get_csrf_token()}">
            <label>Name<input name="name" autocomplete="name" value="#{h(Map.get(params, "name", ""))}"></label>
            <label>Email<input name="email" type="email" autocomplete="username" value="#{h(Map.get(params, "email", ""))}"></label>
            <label>Password<input name="password" type="password" autocomplete="new-password"></label>
            <button type="submit">Create account</button>
          </form>
          <p class="form-footer"><a href="/login">Back to sign in</a></p>
        </div>
      </section>
    </body>
    </html>
    """
  end

  def otp_page(error \\ nil) do
    """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DuckExchange Verification</title>
      <style>#{style()}</style>
    </head>
    <body class="login-page">
      <section class="login-shell otp-shell">
        <div class="brand-panel">
          <div class="brand-mark">DE</div>
          <p class="eyebrow">Step-up verification</p>
          <h1>Confirm the analyst sign-in.</h1>
          <p class="lede">
            A short-lived verification code was queued for the account email before opening the
            delivery operations console.
          </p>
          <div class="signal-grid">
            <div><span>Session</span><strong>Established</strong></div>
            <div><span>Verification</span><strong>Pending</strong></div>
            <div><span>Retry Policy</span><strong>Limited</strong></div>
          </div>
        </div>
        <div class="login-card">
          <p class="eyebrow">Email verification</p>
          <h2>Enter your one-time code</h2>
          <p class="muted">
            Codes expire quickly. Multiple failed attempts temporarily lock verification.
          </p>
          #{alert(error)}
          <form method="post" action="/otp">
            <input type="hidden" name="_csrf_token" value="#{Plug.CSRFProtection.get_csrf_token()}">
            <label>One-time code<input name="otp" inputmode="numeric" autocomplete="one-time-code" maxlength="6"></label>
            <button type="submit">Verify code</button>
          </form>
        </div>
      </section>
    </body>
    </html>
    """
  end

  defp render_inbox(conn, _params) do
    case current_tenant(conn) do
      nil ->
        conn
        |> put_status(:forbidden)
        |> html(forbidden_page("/inbox"))

      tenant ->
        docs = Documents.list_for_tenant_slug(tenant.slug)

        cards =
          Enum.map_join(docs, "\n", fn doc ->
            """
            <article class="doc-row">
              <div>
                <span class="badge #{h(doc.classification)}">#{h(doc.classification)}</span>
                <h3>#{h(doc.title)}</h3>
                <p>#{h(String.slice(doc.body, 0, 118))}</p>
              </div>
              <div class="doc-meta">
                <span>Document ID</span>
                <code>#{h(doc.id)}</code>
                <a class="ghost-button" href="/api/v1/tenants/#{tenant.slug}/documents/#{doc.id}">Open API object</a>
              </div>
            </article>
            """
          end)

        external_notice = """
        <section class="risk-panel">
          <div>
            <p class="eyebrow">External delivery queue</p>
            <h2>Partner incident packet awaiting tenant verification</h2>
            <p>
              A sealed Initech legal delivery was indexed by the exchange router but blocked by
              tenant policy. Analysts can check the routing reference while ownership verification
              is pending.
            </p>
          </div>
          <div class="route-box">
            <span>Delivery reference</span>
            <code>IR-4472</code>
            <a class="ghost-button" href="/exchange/lookup">Check delivery state</a>
            <small>Policy result: tenant denied</small>
          </div>
        </section>
        """

        body = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>DuckExchange Inbox</title>
          <style>#{style()}</style>
          <script>
          // dashboard metrics bootstrap; docs index disabled in this build
          const DOCS_PATH = "/docs/";
          function initMetrics(){ /* no-op */ }
          </script>
        </head>
        <body>
          <aside class="sidebar">
            <div class="brand-line"><span class="brand-mark small">DE</span><strong>Duck Exchange</strong></div>
            <nav>
              <a class="active" href="/inbox">Inbox</a>
              <a href="/">Workspace</a>
            </nav>
            <form method="post" action="/logout">
              <input type="hidden" name="_csrf_token" value="#{Plug.CSRFProtection.get_csrf_token()}">
              <button class="secondary" type="submit">Sign out</button>
            </form>
          </aside>
          <main class="dashboard">
            <header class="topbar">
              <div>
                <p class="eyebrow">#{h(tenant.slug)} / delivery operations</p>
                <h1>Review queue for #{h(tenant.name)}</h1>
              </div>
              <div class="tenant-chip">Identity status: <strong>Email verification pending</strong></div>
            </header>
            <section class="metrics">
              <div><span>Owned objects</span><strong>#{length(docs)}</strong></div>
              <div><span>Blocked external</span><strong>1</strong></div>
              <div><span>API Gateway</span><strong>Online</strong></div>
              <div><span>Policy mode</span><strong>Tenant scoped</strong></div>
            </section>
            <section class="content-grid">
              <div class="queue-panel">
                <div class="section-title">
                  <div>
                    <p class="eyebrow">Tenant documents</p>
                    <h2>Acme-owned delivery objects</h2>
                  </div>
                  <span class="status-dot">Synced</span>
                </div>
                #{cards}
              </div>
              <aside class="activity-panel">
                <p class="eyebrow">Gateway activity</p>
                <h2>Recent decisions</h2>
                <ol>
                  <li><span>Policy allowed</span><strong>GET /tenants/acme-corp/documents</strong></li>
                  <li><span>Index sync</span><strong>External object metadata received</strong></li>
                  <li><span>Policy denied</span><strong>Tenant mismatch on Initech route</strong></li>
                </ol>
              </aside>
            </section>
            #{external_notice}
          </main>
        </body>
        </html>
        """

        html(conn, body)
    end
  end

  def exchange_lookup(conn, %{"q" => ref}) do
    case current_tenant(conn) do
      nil ->
        conn
        |> put_status(:forbidden)
        |> html(forbidden_page("/exchange/lookup"))

      tenant ->
        ref = to_string(ref)
        trimmed_ref = String.trim(ref)

        status =
          if trimmed_ref == "" do
            nil
          else
            case Documents.external_delivery_probe(ref) do
              :matched -> "Pending tenant verification"
              :not_matched -> "No routed object found"
            end
          end

        status_markup =
          case status do
            nil -> ~s(<strong class="status-empty" aria-label="No lookup submitted"></strong>)
            value -> "<strong>#{value}</strong>"
          end

        body = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Duck Exchange Lookup</title>
          <style>#{style()}</style>
        </head>
        <body>
          <main class="lookup-page">
            <section class="lookup-card">
              <p class="eyebrow">#{h(tenant.slug)} / exchange lookup</p>
              <h1>Delivery reference lookup</h1>
              <form method="get" action="/exchange/lookup">
                <label>Reference<input name="q" value="#{h(if(trimmed_ref == "", do: "", else: ref))}" placeholder="Enter delivery reference"></label>
                <button type="submit">Check delivery state</button>
              </form>
              <div class="lookup-result">
                <span>Router state</span>
                #{status_markup}
              </div>
              <p><a href="/inbox">Back to inbox</a></p>
            </section>
          </main>
        </body>
        </html>
        """

        html(conn, body)
    end
  end

  def exchange_lookup(conn, _params) do
    exchange_lookup(conn, %{"q" => ""})
  end

  def not_found(conn, _params) do
    conn
    |> put_status(:not_found)
    |> html("not found")
  end

  defp alert(nil), do: ""
  defp alert(""), do: ""

  defp alert(message) do
    """
    <div class="alert">#{h(message)}</div>
    """
  end

  defp session_panel(nil), do: ""

  defp session_panel(tenant) do
    """
    <div class="session-banner">
      Signed in as <strong>#{h(tenant.name)}</strong>.
      <form method="post" action="/logout" style="display:inline">
        <input type="hidden" name="_csrf_token" value="#{Plug.CSRFProtection.get_csrf_token()}">
        <button type="submit">Sign out</button>
      </form>
      <p><a href="/inbox">Open inbox</a></p>
    </div>
    """
  end

  defp current_tenant(conn) do
    conn
    |> fetch_cookies()
    |> Map.get(:cookies)
    |> Map.get(Accounts.session_cookie())
    |> Accounts.tenant_for_session()
  end

  defp h(value) do
    value
    |> to_string()
    |> String.replace("&", "&amp;")
    |> String.replace("<", "&lt;")
    |> String.replace(">", "&gt;")
    |> String.replace("\"", "&quot;")
  end

  defp style do
    """
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #657386;
      --line: #dce3ec;
      --panel: #ffffff;
      --soft: #f5f7fb;
      --accent: #2457d6;
      --accent-dark: #183b94;
      --teal: #0f766e;
      --gold: #b7791f;
      --warn: #a85d00;
      --danger: #a63232;
      --ok: #14724d;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #f1f4f8;
    }

    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    code {
      display: inline-block;
      max-width: 100%;
      overflow-wrap: anywhere;
      border: 1px solid #d9e1ed;
      border-radius: 6px;
      padding: .2rem .38rem;
      background: #f8fafc;
      color: #263142;
      font-size: .86rem;
    }

    .login-page {
      display: grid;
      place-items: center;
      padding: 32px;
      background:
        linear-gradient(135deg, rgba(36, 87, 214, .12), transparent 44%),
        linear-gradient(315deg, rgba(15, 118, 110, .09), transparent 40%),
        #f1f4f8;
    }

    .login-shell {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, .8fr);
      width: min(1080px, 100%);
      min-height: 620px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: var(--panel);
      box-shadow: 0 24px 70px rgba(36, 45, 64, .16);
    }

    .otp-shell { min-height: 560px; }

    .brand-panel {
      padding: 56px;
      color: white;
      background:
        linear-gradient(rgba(18, 27, 42, .82), rgba(18, 27, 42, .82)),
        linear-gradient(135deg, #18283b, #28536b 52%, #35665f);
    }

    .brand-mark {
      display: grid;
      place-items: center;
      width: 52px;
      height: 52px;
      border-radius: 8px;
      background: #ffffff;
      color: var(--accent-dark);
      font-weight: 800;
      letter-spacing: 0;
    }

    .brand-mark.small { width: 34px; height: 34px; font-size: .8rem; border: 1px solid var(--line); }
    .eyebrow {
      margin: 0 0 10px;
      color: inherit;
      opacity: .72;
      font-size: .78rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    h1, h2, h3, p { margin-top: 0; }
    h1 { font-size: clamp(2rem, 4vw, 3.8rem); line-height: 1.02; max-width: 760px; }
    h2 { font-size: 1.25rem; margin-bottom: .45rem; }
    h3 { font-size: 1rem; margin-bottom: .25rem; }
    .lede { max-width: 620px; color: rgba(255,255,255,.78); font-size: 1.05rem; line-height: 1.65; }
    .muted { color: var(--muted); }

    .system-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 28px;
    }
    .system-strip span {
      border: 1px solid rgba(255,255,255,.24);
      border-radius: 999px;
      padding: .42rem .62rem;
      background: rgba(255,255,255,.09);
      color: rgba(255,255,255,.82);
      font-size: .78rem;
      font-weight: 750;
    }

    .signal-grid, .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 44px;
    }

    .signal-grid div, .metrics div {
      border: 1px solid rgba(255,255,255,.24);
      border-radius: 8px;
      padding: 14px;
      background: rgba(255,255,255,.08);
    }

    .signal-grid span, .metrics span, .route-box span, .doc-meta span, .activity-panel li span {
      display: block;
      color: var(--muted);
      font-size: .78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .signal-grid span { color: rgba(255,255,255,.66); }
    .signal-grid strong, .metrics strong { display: block; margin-top: 6px; font-size: 1rem; }

    .login-card { padding: 56px 44px; align-self: center; }
    label { display: block; margin: 18px 0 0; color: var(--muted); font-size: .9rem; font-weight: 700; }
    input {
      width: 100%;
      margin-top: 8px;
      border: 1px solid #cbd5e1;
      border-radius: 7px;
      padding: .82rem .9rem;
      font: inherit;
      color: var(--ink);
      background: white;
    }
    button, .ghost-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      border: 0;
      border-radius: 7px;
      padding: .75rem 1rem;
      font: inherit;
      font-weight: 800;
      background: var(--accent);
      color: white;
      cursor: pointer;
    }
    button:hover, .ghost-button:hover { background: var(--accent-dark); text-decoration: none; }
    .secondary { width: 100%; background: #e7edf6; color: var(--ink); }
    .secondary:hover { background: #d7e1ef; }
    .form-footer { margin: 18px 0 0; font-size: .92rem; }
    .alert {
      border: 1px solid #f2c1c1;
      border-radius: 8px;
      padding: .8rem .9rem;
      margin: 16px 0;
      background: #fff2f2;
      color: var(--danger);
      font-weight: 750;
    }
    .session-banner {
      border: 1px solid #cad6e6;
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 22px;
      background: #f7f9fc;
    }

    .sidebar {
      position: fixed;
      inset: 0 auto 0 0;
      width: 250px;
      padding: 22px;
      border-right: 1px solid var(--line);
      background: #fbfcfe;
      box-shadow: 8px 0 30px rgba(36, 45, 64, .035);
    }
    .brand-line { display: flex; align-items: center; gap: 10px; margin-bottom: 34px; }
    nav { display: grid; gap: 8px; margin-bottom: 28px; }
    nav a {
      border-radius: 7px;
      padding: .75rem .85rem;
      color: var(--muted);
      font-weight: 750;
    }
    nav a.active, nav a:hover { background: #e9eef7; color: var(--ink); text-decoration: none; }

    .dashboard { margin-left: 250px; padding: 30px; }
    .topbar, .section-title, .risk-panel {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 24px;
    }
    .tenant-chip, .status-dot {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: .55rem .8rem;
      background: white;
      color: var(--muted);
      white-space: nowrap;
    }
    .metrics {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin: 22px 0;
    }
    .metrics div {
      border-color: var(--line);
      background: white;
    }

    .content-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 22px;
      align-items: start;
    }
    .queue-panel, .activity-panel, .risk-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 22px;
      box-shadow: 0 12px 28px rgba(36, 45, 64, .055);
    }
    .doc-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(230px, .42fr);
      gap: 18px;
      padding: 18px 0;
      border-top: 1px solid var(--line);
    }
    .doc-row p { color: var(--muted); line-height: 1.55; margin-bottom: 0; }
    .doc-meta { display: grid; gap: 8px; justify-items: start; }
    .badge {
      display: inline-flex;
      border-radius: 999px;
      padding: .28rem .5rem;
      margin-bottom: .55rem;
      font-size: .72rem;
      font-weight: 800;
      text-transform: uppercase;
      background: #e9eef7;
      color: var(--accent-dark);
    }
    .badge.confidential { background: #fff3dc; color: var(--warn); }
    .badge.restricted { background: #fde7e7; color: var(--danger); }

    .activity-panel ol { list-style: none; padding: 0; margin: 16px 0 0; display: grid; gap: 16px; }
    .activity-panel li { border-top: 1px solid var(--line); padding-top: 14px; }
    .activity-panel strong { display: block; margin-top: 6px; font-size: .92rem; }
    .risk-panel { margin-top: 22px; background: #fffaf2; border-color: #f1d9a8; }
    .risk-panel p { color: #65543b; line-height: 1.55; max-width: 680px; margin-bottom: 0; }
    .route-box {
      min-width: min(420px, 100%);
      border: 1px solid #edcf91;
      border-radius: 8px;
      padding: 14px;
      background: #fffdf7;
    }
    .route-box small { display: block; margin-top: 10px; color: var(--danger); font-weight: 800; }

    .lookup-page {
      display: grid;
      place-items: center;
      min-height: 100vh;
      padding: 28px;
    }
    .lookup-card {
      width: min(640px, 100%);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      background: white;
      box-shadow: 0 18px 55px rgba(36, 45, 64, .12);
    }
    .lookup-card h1 { font-size: 2rem; }
    .lookup-result {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      margin: 18px 0;
      background: #f8fafc;
    }
    .lookup-result span {
      display: block;
      color: var(--muted);
      font-size: .78rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }
    .lookup-result strong { display: block; margin-top: 6px; }

    @media (max-width: 900px) {
      .login-shell, .content-grid, .doc-row, .metrics, .signal-grid { grid-template-columns: 1fr; }
      .brand-panel, .login-card { padding: 32px; }
      .sidebar { position: static; width: auto; border-right: 0; border-bottom: 1px solid var(--line); }
      .dashboard { margin-left: 0; padding: 20px; }
      .topbar, .section-title, .risk-panel { display: grid; }
      .tenant-chip { white-space: normal; }
    }
    """
  end
end
