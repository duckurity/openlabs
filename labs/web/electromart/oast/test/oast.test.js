'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')

const { loadConfig } = require('../src/config')
const { createApp } = require('../src/app')
const { InteractionStore, isValidCallbackId } = require('../src/store')
const { escapeHtml } = require('../src/dashboard')

const silentLogger = { debug() {}, info() {}, warn() {}, error() {} }

async function startService(env = {}) {
  const { config, warnings } = loadConfig({ OAST_PUBLIC_URL: 'http://attckerserver.local:4000', ...env })
  assert.deepEqual(warnings, [])
  const store = new InteractionStore({ max: config.maxInteractions })
  const { app } = createApp({ config, logger: silentLogger, store })
  const server = await new Promise((resolve, reject) => {
    const instance = app.listen(0, '127.0.0.1', () => resolve(instance))
    instance.on('error', reject)
  })
  const base = `http://127.0.0.1:${server.address().port}`
  return {
    base,
    store,
    config,
    async close() {
      await new Promise((resolve) => server.close(resolve))
    },
  }
}

test('OAST config defaults and callback origin are lab-scoped', () => {
  const { config, warnings } = loadConfig({})
  assert.equal(config.port, 4000)
  assert.equal(config.publicOrigin, 'http://attckerserver.local:4000')
  assert.equal(config.maxBodyBytes, 16 * 1024)
  assert.equal(config.maxInteractions, 1000)
  assert.equal(typeof config.buildId, 'string')
  assert.ok(config.buildId.length > 0)
  assert.deepEqual(warnings, [])
})

test('OAST config rejects an invalid public hostname and URL safely', () => {
  const { config, warnings } = loadConfig({
    OAST_PUBLIC_HOST: 'http://evil.test/path',
    OAST_PUBLIC_URL: 'http://user:pass@evil.test',
  })
  assert.equal(config.publicOrigin, 'http://attckerserver.local:4000')
  assert.ok(warnings.some((warning) => warning.includes('OAST_PUBLIC_HOST')))
  assert.ok(warnings.some((warning) => warning.includes('OAST_PUBLIC_URL')))
})

test('Test A: health endpoint reports the OAST service as ready', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  for (const endpoint of ['/health', '/api/health']) {
    const response = await fetch(`${service.base}${endpoint}`)
    assert.equal(response.status, 200)
    const payload = await response.json()
    assert.equal(payload.status, 'ok')
    assert.equal(payload.service, 'oast')
    assert.equal(payload.callbackOrigin, 'http://attckerserver.local:4000')
    assert.equal(typeof payload.buildId, 'string')
    assert.ok(payload.buildId.length > 0)
    assert.equal(payload.interactions.totalRecorded, 0)
  }
})

test('Test B: unique callback IDs are generated and every valid callback is recorded', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const first = await fetch(`${service.base}/api/callbacks`, { method: 'POST' })
  const second = await fetch(`${service.base}/api/callbacks`, { method: 'POST' })
  assert.equal(first.status, 201)
  assert.equal(second.status, 201)
  const a = await first.json()
  const b = await second.json()
  assert.notEqual(a.id, b.id)
  assert.ok(isValidCallbackId(a.id))
  assert.equal(a.callbackUrl, `http://attckerserver.local:4000/c/${a.id}`)

  const requestBody = 'hello <world> & "quotes"'
  const response = await fetch(`${service.base}/c/${a.id}?probe=one&tag=%3Ctest%3E`, {
    method: 'POST',
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'x-oast-test': 'alpha',
      cookie: 'session=synthetic-lab-value',
    },
    body: requestBody,
  })
  assert.equal(response.status, 200)
  assert.match(await response.text(), /Callback recorded/)

  const list = await (await fetch(`${service.base}/api/interactions?callbackId=${a.id}`)).json()
  assert.equal(list.status, 'ok')
  assert.equal(list.count, 1)
  assert.equal(list.total, 1)
  const hit = list.interactions[0]
  assert.equal(hit.callbackId, a.id)
  assert.equal(hit.method, 'POST')
  assert.equal(hit.endpoint, `/c/${a.id}`)
  assert.equal(hit.validation, 'accepted')
  assert.equal(hit.url, `/c/${a.id}?probe=one&tag=%3Ctest%3E`)
  assert.equal(hit.query, '?probe=one&tag=%3Ctest%3E')
  assert.equal(hit.headers['x-oast-test'], 'alpha')
  assert.equal(hit.headers.cookie, 'session=synthetic-lab-value')
  assert.equal(hit.contentType, 'text/plain; charset=utf-8')
  assert.equal(hit.body, requestBody)
  assert.equal(hit.bodyEncoding, 'utf8')
  assert.equal(hit.bodyBytes, Buffer.byteLength(requestBody))
  assert.ok(hit.rawHeaders.some((entry) => String(entry).toLowerCase() === 'x-oast-test'))
  assert.match(hit.sourceAddress, /127\.0\.0\.1|::1/)
  assert.ok(Number.isInteger(hit.sourcePort))
  assert.equal(hit.httpVersion, '1.1')
  assert.ok(hit.timestamp)

  // A second callback ID remains distinguishable and captures its own body.
  await fetch(`${service.base}/c/${b.id}`, { method: 'POST', body: 'small harmless marker', headers: { 'content-type': 'text/plain' } })
  const bList = await (await fetch(`${service.base}/api/interactions?callbackId=${b.id}`)).json()
  assert.equal(bList.count, 1)
  assert.equal(bList.interactions[0].method, 'POST')
  assert.equal(bList.interactions[0].body, 'small harmless marker')
  assert.equal(service.store.stats().uniqueCallbackIds, 2)
})

test('Test B: malformed callback paths are rejected and not recorded', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  for (const path of ['/c/short', '/c/bad!identifier', '/c/' + 'x'.repeat(80)]) {
    const response = await fetch(`${service.base}${path}`)
    assert.equal(response.status, 400, path)
    const payload = await response.json()
    assert.equal(payload.error, 'invalid-callback-id')
  }

  const list = await (await fetch(`${service.base}/api/interactions`)).json()
  assert.equal(list.total, 0)
  assert.equal(service.store.stats().totalRejected, 3)
})

test('Test B: oversized callback and API bodies fail safely without recording', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const id = 'a'.repeat(24)
  const oversized = await fetch(`${service.base}/c/${id}`, {
    method: 'POST',
    headers: { 'content-type': 'text/plain' },
    body: 'x'.repeat(20 * 1024),
  })
  assert.equal(oversized.status, 413)
  assert.equal((await oversized.json()).error, 'payload-too-large')

  const malformedJson = await fetch(`${service.base}/api/callbacks`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: '{not-json',
  })
  assert.equal(malformedJson.status, 400)
  assert.equal((await malformedJson.json()).error, 'malformed-request')

  const list = await (await fetch(`${service.base}/api/interactions?callbackId=${id}`)).json()
  assert.equal(list.total, 0)
})

test('Test B: dashboard displays escaped request headers and body', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const id = 'dashboard-example-0001'
  const body = '<script>alert("dashboard-body")</script>'
  await fetch(`${service.base}/c/${id}?probe=%3Cscript%3E`, {
    method: 'POST',
    headers: {
      'content-type': 'text/plain',
      'x-dashboard-test': '<b>header-value</b>',
    },
    body,
  })
  const response = await fetch(`${service.base}/`)
  assert.equal(response.status, 200)
  const html = await response.text()
  assert.match(html, /ElectroMart <span>OAST<\/span>/)
  assert.match(html, new RegExp(id))
  assert.match(html, /accepted/)
  assert.match(html, /attckerserver\.local:4000\/c\//)
  assert.match(html, /Request data for #1/)
  assert.match(html, /x-dashboard-test/)
  assert.match(html, /&lt;b&gt;header-value&lt;\/b&gt;/)
  assert.match(html, /&lt;script&gt;alert\(&quot;dashboard-body&quot;\)&lt;\/script&gt;/)
  assert.doesNotMatch(html, /<script>alert\("dashboard-body"\)<\/script>/)
  assert.doesNotMatch(html, /<b>header-value<\/b>/)

  const stats = await (await fetch(`${service.base}/api/stats`)).json()
  assert.equal(stats.status, 'ok')
  assert.equal(stats.stats.totalRecorded, 1)
  assert.equal(stats.stats.uniqueCallbackIds, 1)
})

test('Test B: JSON callback bodies are captured raw instead of being parsed away', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const id = 'json-body-example'
  const rawBody = '{"name":"lab","nested":{"value":"<tag>"}}'
  await fetch(`${service.base}/c/${id}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: rawBody,
  })
  const list = await (await fetch(`${service.base}/api/interactions?callbackId=${id}`)).json()
  const hit = list.interactions[0]
  assert.equal(hit.contentType, 'application/json')
  assert.equal(hit.body, rawBody)
  assert.equal(hit.bodyBytes, Buffer.byteLength(rawBody))
})

test('Test B: non-UTF-8 bodies are preserved exactly as Base64', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const id = 'binary-body-example'
  const bytes = Buffer.from([0xff, 0xfe, 0x00, 0x41, 0x80])
  await fetch(`${service.base}/c/${id}`, {
    method: 'POST',
    headers: { 'content-type': 'application/octet-stream' },
    body: bytes,
  })
  const list = await (await fetch(`${service.base}/api/interactions?callbackId=${id}`)).json()
  const hit = list.interactions[0]
  assert.equal(hit.bodyEncoding, 'base64')
  assert.equal(hit.body, bytes.toString('base64'))
  assert.equal(hit.bodyBytes, bytes.length)
})

test('Dashboard escaping neutralises HTML metacharacters', () => {
  assert.equal(
    escapeHtml('<script>alert("x")</script>'),
    '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
  )
})

test('Unknown routes return a JSON 404 and CORS does not allow credentials', async (t) => {
  const service = await startService()
  t.after(() => service.close())

  const response = await fetch(`${service.base}/not-a-route`)
  assert.equal(response.status, 404)
  assert.equal((await response.json()).error, 'not-found')
  assert.equal(response.headers.get('access-control-allow-origin'), '*')
  assert.equal(response.headers.get('access-control-allow-credentials'), null)
})
