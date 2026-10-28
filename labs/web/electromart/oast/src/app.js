'use strict'

const express = require('express')

const { renderDashboard, escapeHtml } = require('./dashboard')
const {
  InteractionStore,
  newCallbackId,
  isValidCallbackId,
  safeEndpoint,
} = require('./store')

const CALLBACK_PREFIXES = ['/c', '/cb', '/callback']

function wantsJson(req) {
  if (String(req.query.format || '').toLowerCase() === 'json') return true
  const accept = String(req.get('accept') || '')
  return accept.includes('application/json') && !accept.includes('text/html')
}

function callbackPage(callbackId, publicOrigin) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OAST callback recorded</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #0b1020; color: #e7ecff;
      font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    .box { max-width: 640px; padding: 28px; border: 1px solid #263255; border-radius: 16px;
      background: #131a2e; }
    h1 { margin: 0 0 8px; font-size: 20px; color: #43d68a; }
    code { background: #0a1022; border: 1px solid #263255; border-radius: 6px;
      padding: 2px 6px; color: #cfe0ff; word-break: break-all; }
    p { color: #93a0c4; margin: 10px 0 0; }
  </style>
</head>
<body>
  <main class="box">
    <h1>Callback recorded</h1>
    <p>Callback identifier: <code>${escapeHtml(callbackId)}</code></p>
    <p>The interaction was accepted by the ElectroMart OAST service. View it on the
      <a style="color:#7c9cff" href="${escapeHtml(publicOrigin)}/">interaction dashboard</a>.</p>
    <p>Request headers, query string, and body are available on the dashboard.
      This is a lab service: only send synthetic data.</p>
  </main>
</body>
</html>`
}

/**
 * Build the OAST Express application.
 *
 * @param {{config: object, logger: object, store?: InteractionStore}} options
 */
function createApp({ config, logger, store = new InteractionStore({ max: config.maxInteractions }) }) {
  const app = express()
  const startedAt = Date.now()

  app.disable('x-powered-by')
  app.set('trust proxy', false) // Record the real socket source, not spoofable headers.

  // Conservative headers. The callback and dashboard are intentionally readable
  // by the lab browser, so cross-origin resource policy is not locked down; the
  // service itself is only reachable on the internal network/localhost binding.
  app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff')
    res.setHeader('Referrer-Policy', 'no-referrer')
    res.setHeader('X-Frame-Options', 'DENY')
    res.setHeader('Cache-Control', 'no-store')
    res.setHeader('Content-Security-Policy',
      "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
    // A player may use fetch() from the browser lab origin. No credentials are
    // accepted or stored, so a wildcard origin is appropriate here.
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    res.setHeader('Access-Control-Max-Age', '600')
    next()
  })

  // Reject over-long URLs before routing/parsing.
  app.use((req, res, next) => {
    if (String(req.originalUrl || '').length > 1024) {
      store.noteRejected()
      logger.warn('oast.request-rejected', { reason: 'url-too-long' })
      return res.status(414).json({ status: 'error', error: 'uri-too-long' })
    }
    next()
  })

  app.options('*', (req, res) => res.status(204).end())

  // Callback bodies are read as raw bytes first so the dashboard can display
  // exactly what arrived. API endpoints still use the normal JSON parser.
  for (const prefix of CALLBACK_PREFIXES) {
    app.use(prefix, express.raw({ type: () => true, limit: config.maxBodyBytes }))
  }
  app.use(express.json({ limit: config.maxBodyBytes, strict: true }))
  app.use(express.urlencoded({ extended: false, limit: config.maxBodyBytes }))

  // ---------- Health ----------
  const health = (req, res) => {
    res.json({
      status: 'ok',
      service: 'oast',
      time: new Date().toISOString(),
      uptimeSeconds: Math.floor((Date.now() - startedAt) / 1000),
      interactions: store.stats(),
      callbackOrigin: config.publicOrigin,
      buildId: config.buildId,
    })
  }
  app.get('/health', health)
  app.get('/api/health', health)

  // ---------- Dashboard ----------
  const dashboard = (req, res) => {
    const interactions = store.list({ limit: config.dashboardLimit })
    const sampleId = newCallbackId()
    res.type('html').send(
      renderDashboard({
        interactions,
        stats: store.stats(),
        sampleUrl: `${config.publicOrigin}/c/${sampleId}`,
        publicOrigin: config.publicOrigin,
        uptimeSeconds: (Date.now() - startedAt) / 1000,
        now: new Date().toISOString(),
        buildId: config.buildId,
      })
    )
  }
  app.get('/', dashboard)
  app.get('/dashboard', dashboard)

  // ---------- Callback endpoints ----------
  const recordCallback = (req, res) => {
    const callbackId = String(req.params.id || '')
    if (!isValidCallbackId(callbackId)) {
      store.noteRejected()
      logger.warn('oast.callback-rejected', {
        reason: 'invalid-callback-id',
        method: req.method,
        endpoint: safeEndpoint(req.path),
      })
      return res.status(400).json({ status: 'error', error: 'invalid-callback-id' })
    }

    const interaction = store.record({
      callbackId,
      method: req.method,
      endpoint: req.path,
      sourceAddress: req.socket && req.socket.remoteAddress,
      remotePort: req.socket && req.socket.remotePort,
      validation: 'accepted',
      protocol: req.protocol,
      httpVersion: req.httpVersion,
      url: req.originalUrl,
      headers: req.headers,
      rawHeaders: req.rawHeaders,
      body: Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0),
    })

    // Logs stay metadata-only; full headers/body are visible on the dashboard
    // and through the JSON API so docker logs do not become a secret leak.
    logger.info('oast.interaction', {
      interactionId: interaction.id,
      callbackId: interaction.callbackId,
      method: interaction.method,
      endpoint: interaction.endpoint,
      sourceAddress: interaction.sourceAddress,
      validation: interaction.validation,
      bodyBytes: interaction.bodyBytes,
      headerCount: Object.keys(interaction.headers).length,
    })

    if (wantsJson(req)) {
      return res.status(200).json({ status: 'accepted', interaction })
    }
    if (req.method === 'HEAD') return res.status(200).end()
    return res.status(200).type('html').send(callbackPage(callbackId, config.publicOrigin))
  }

  for (const prefix of CALLBACK_PREFIXES) {
    app.all(`${prefix}/:id`, recordCallback)
  }

  // ---------- JSON API ----------
  const createCallback = (req, res) => {
    const id = newCallbackId()
    res.status(201).json({
      status: 'ok',
      id,
      callbackUrl: `${config.publicOrigin}/c/${id}`,
      createdAt: new Date().toISOString(),
    })
  }
  app.post('/api/callbacks', createCallback)
  app.get('/api/callbacks/new', createCallback)

  app.get('/api/interactions', (req, res) => {
    const callbackId = req.query.callbackId === undefined ? null : String(req.query.callbackId)
    if (callbackId !== null && !isValidCallbackId(callbackId)) {
      return res.status(400).json({ status: 'error', error: 'invalid-callback-id' })
    }

    const parsedLimit = Number(req.query.limit)
    const limit = Number.isInteger(parsedLimit)
      ? Math.max(1, Math.min(parsedLimit, 200))
      : config.dashboardLimit

    const interactions = store.list({ callbackId, limit })
    return res.json({
      status: 'ok',
      count: interactions.length,
      total: store.countFor(callbackId),
      interactions,
    })
  })

  app.get('/api/interactions/:interactionId', (req, res) => {
    const wanted = Number(req.params.interactionId)
    const item = Number.isInteger(wanted)
      ? store.list({ limit: 1000 }).find((entry) => entry.id === wanted)
      : null
    if (!item) return res.status(404).json({ status: 'error', error: 'not-found' })
    return res.json({ status: 'ok', interaction: item })
  })

  app.get('/api/stats', (req, res) => {
    res.json({ status: 'ok', stats: store.stats(), uptimeSeconds: Math.floor((Date.now() - startedAt) / 1000) })
  })

  // ---------- Fallbacks ----------
  app.use((req, res) => {
    res.status(404).json({ status: 'error', error: 'not-found' })
  })

  // Express error handler: never echo a request body or header value.
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error)
    const status = error && (error.status || error.statusCode)
    const safeStatus = [400, 413, 414, 415, 422].includes(status) ? status : 500
    const code = safeStatus === 413
      ? 'payload-too-large'
      : safeStatus === 400
        ? 'malformed-request'
        : 'internal-error'
    store.noteRejected()
    logger.warn('oast.request-rejected', {
      reason: code,
      method: req.method,
      endpoint: safeEndpoint(req.path),
    })
    return res.status(safeStatus).json({ status: 'error', error: code })
  })

  return { app, store }
}

module.exports = { createApp, InteractionStore }
