'use strict'

function escapeHtml(value) {
  return String(value === undefined || value === null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function headerPairs(item) {
  const pairs = []
  const raw = Array.isArray(item.rawHeaders) ? item.rawHeaders : []
  if (raw.length) {
    for (let index = 0; index < raw.length; index += 2) {
      pairs.push([raw[index], index + 1 < raw.length ? raw[index + 1] : ''])
    }
    return pairs
  }
  for (const [name, value] of Object.entries(item.headers || {})) {
    if (Array.isArray(value)) {
      for (const entry of value) pairs.push([name, entry])
    } else {
      pairs.push([name, value])
    }
  }
  return pairs
}

function renderRequestDetails(item) {
  const pairs = headerPairs(item)
  const headerRows = pairs.length
    ? pairs
        .map(
          ([name, value]) => `
            <tr>
              <td class="hname"><code>${escapeHtml(name)}</code></td>
              <td><code>${escapeHtml(value)}</code></td>
            </tr>`
        )
        .join('')
    : '<tr><td colspan="2" class="muted">No headers recorded.</td></tr>'

  const source = item.sourcePort
    ? `${item.sourceAddress}:${item.sourcePort}`
    : item.sourceAddress
  const bodyLabel = item.bodyEncoding === 'base64'
    ? `body: Base64 · ${item.bodyBytes} bytes`
    : `body: UTF-8 · ${item.bodyBytes} bytes`
  const bodyText = item.bodyBytes === 0 ? '(empty)' : item.body

  return `
        <tr class="details-row">
          <td colspan="7">
            <details class="request">
              <summary>Request data for #${escapeHtml(item.id)} — ${escapeHtml(item.method)} ${escapeHtml(item.endpoint)}</summary>
              <div class="request-body">
                <div class="request-line"><code>${escapeHtml(item.requestLine)}</code></div>
                <div class="request-meta">
                  <span>protocol ${escapeHtml(item.protocol || 'http')}</span>
                  <span>source ${escapeHtml(source)}</span>
                  <span>query ${escapeHtml(item.query || '(none)')}</span>
                  <span>${escapeHtml(bodyLabel)}</span>
                  ${item.contentType ? `<span>content-type ${escapeHtml(item.contentType)}</span>` : ''}
                </div>
                <div class="detail-grid">
                  <section>
                    <h3>Headers</h3>
                    <div class="header-scroll">
                      <table class="headers"><tbody>${headerRows}</tbody></table>
                    </div>
                  </section>
                  <section>
                    <h3>Body</h3>
                    <pre>${escapeHtml(bodyText)}</pre>
                  </section>
                </div>
              </div>
            </details>
          </td>
        </tr>`
}

/**
 * Self-contained graphical dashboard. Values are escaped because interactions
 * carry arbitrary request-derived strings (request line, headers, body, and
 * source address); the callback identifier is also validated before storage.
 */
function renderDashboard({
  interactions,
  stats,
  sampleUrl,
  publicOrigin,
  uptimeSeconds,
  now,
  buildId,
}) {
  const rows = interactions.length
    ? interactions
        .map(
          (item) => `
          <tr>
            <td class="num">${escapeHtml(item.id)}</td>
            <td class="muted">${escapeHtml(item.timestamp)}</td>
            <td><code class="id">${escapeHtml(item.callbackId)}</code></td>
            <td><span class="method">${escapeHtml(item.method)}</span></td>
            <td><code>${escapeHtml(item.endpoint)}</code></td>
            <td class="muted">${escapeHtml(item.sourceAddress)}</td>
            <td><span class="ok">${escapeHtml(item.validation)}</span></td>
          </tr>
          ${renderRequestDetails(item)}`
        )
        .join('')
    : `
      <tr>
        <td colspan="7" class="empty">
          No interactions recorded yet. Use the callback URL above (or a new unique
          <code>/c/&lt;id&gt;</code> path) from the lab.
        </td>
      </tr>`

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ElectroMart OAST — Interactions</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: #131a2e;
      --panel-2: #172039;
      --line: #263255;
      --text: #e7ecff;
      --muted: #93a0c4;
      --accent: #7c9cff;
      --ok: #43d68a;
      --warn: #ffb84d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(1200px 600px at 15% -10%, #1c2b55 0%, var(--bg) 55%);
      color: var(--text);
      font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 28px 20px 48px; }
    header { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; justify-content: space-between; }
    h1 { margin: 0; font-size: 24px; letter-spacing: .2px; }
    h1 span { color: var(--accent); }
    .pill {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 6px 12px; border-radius: 999px;
      background: rgba(67, 214, 138, .12); color: var(--ok);
      border: 1px solid rgba(67, 214, 138, .35); font-weight: 600;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 12px var(--ok); }
    .sub { color: var(--muted); margin: 8px 0 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 18px; }
    .stat { background: linear-gradient(180deg, var(--panel-2), var(--panel)); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; }
    .stat .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .stat .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; margin-bottom: 18px; }
    .card h2 { margin: 0 0 8px; font-size: 15px; }
    .cb { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    code { background: #0a1022; border: 1px solid var(--line); border-radius: 7px; padding: 2px 6px; color: #cfe0ff; word-break: break-all; }
    .cb code { font-size: 13px; padding: 8px 10px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    tr:last-child td { border-bottom: 0; }
    .id { font-size: 12px; }
    .method { font-weight: 700; color: var(--accent); }
    .ok { color: var(--ok); font-weight: 600; }
    .muted { color: var(--muted); }
    .num { color: var(--muted); width: 44px; }
    .empty { text-align: center; color: var(--muted); padding: 28px 10px; }
    .table-scroll { overflow-x: auto; }
    footer { color: var(--muted); font-size: 12px; margin-top: 20px; }
    a { color: var(--accent); }
    .note { color: var(--warn); font-size: 12px; margin-top: 10px; }
    .details-row td { padding: 0 0 10px; border-bottom: 0; }
    details.request { border: 1px solid var(--line); border-radius: 10px; background: #0f1629; }
    details.request summary { cursor: pointer; padding: 10px 12px; color: var(--accent); font-weight: 600; }
    details.request summary:hover { color: #a8bdff; }
    .request-body { padding: 0 12px 14px; }
    .request-line code { display: block; padding: 9px 10px; font-size: 12px; }
    .request-meta { display: flex; flex-wrap: wrap; gap: 7px; margin: 10px 0; color: var(--muted); font-size: 12px; }
    .request-meta span { padding: 3px 8px; border: 1px solid var(--line); border-radius: 999px; background: #0a1022; }
    .detail-grid { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(280px, 1.2fr); gap: 12px; }
    .detail-grid h3 { margin: 0 0 6px; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    .headers td { padding: 6px 8px; font-size: 12px; border-bottom: 1px solid #1b2540; }
    .headers .hname { width: 34%; color: var(--muted); }
    .headers code { background: transparent; border: 0; padding: 0; }
    .header-scroll { max-height: 320px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: #0a1022; }
    pre { margin: 0; padding: 10px; max-height: 320px; overflow: auto; white-space: pre-wrap; word-break: break-word;
      background: #0a1022; border: 1px solid var(--line); border-radius: 8px; color: #cfe0ff;
      font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    @media (max-width: 760px) { .detail-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div>
        <h1>ElectroMart <span>OAST</span></h1>
        <p class="sub">Out-of-band callback observer for the training lab.</p>
      </div>
      <span class="pill"><span class="dot"></span> online · ${escapeHtml(formatDuration(uptimeSeconds))}</span>
    </header>

    <section class="grid" aria-label="Interaction statistics">
      <div class="stat"><div class="label">Interactions</div><div class="value">${escapeHtml(stats.totalRecorded)}</div></div>
      <div class="stat"><div class="label">Retained</div><div class="value">${escapeHtml(stats.retained)}</div></div>
      <div class="stat"><div class="label">Unique IDs</div><div class="value">${escapeHtml(stats.uniqueCallbackIds)}</div></div>
      <div class="stat"><div class="label">Rejected</div><div class="value">${escapeHtml(stats.totalRejected)}</div></div>
      <div class="stat"><div class="label">Capacity</div><div class="value">${escapeHtml(stats.capacity)}</div></div>
    </section>

    <section class="card" aria-label="Callback URL">
      <h2>Callback URL</h2>
      <div class="cb">
        <code id="callback-url">${escapeHtml(sampleUrl)}</code>
        <span class="muted">unique identifier included in the path</span>
      </div>
      <p class="muted" style="margin:10px 0 0">
        Format: <code>${escapeHtml(publicOrigin)}/c/&lt;callback-id&gt;</code>.
        Every accepted request records its request line, source address, query
        string, all headers, and raw body. Bodies are capped by
        <code>OAST_MAX_BODY_BYTES</code>; non-UTF-8 bodies are shown as Base64.
      </p>
      <p class="note">Request details may include cookies, authorization headers, or other sensitive lab data. The dashboard is available only through the lab network and the localhost-only host binding. It no longer auto-refreshes; use the Refresh link below. A new OAST image build starts with an empty interaction list.</p>
    </section>

    <section class="card" aria-label="Recorded interactions">
      <h2>Recorded interactions</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Timestamp (UTC)</th><th>Callback ID</th><th>Method</th>
              <th>Endpoint</th><th>Source address</th><th>Validation</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>

    <footer>
      Health: <a href="/health">/health</a> ·
      JSON API: <a href="/api/interactions">/api/interactions</a> ·
      <a href="/">Refresh</a> ·
      Build: <code>${escapeHtml(buildId || 'dev')}</code> ·
      Snapshot time: ${escapeHtml(now)}
    </footer>
  </main>
</body>
</html>`
}

module.exports = { renderDashboard, escapeHtml }
