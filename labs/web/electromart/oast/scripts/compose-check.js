'use strict'

/* Run inside the bot container:
 *   docker compose exec -T bot node - < oast/test/compose-check.js
 * Verifies OAST availability, callback reception, request header/body capture,
 * malformed input handling, and the dashboard. Exits non-zero on any failure.
 */

async function main() {
  const base = process.env.OAST_BASE_URL || 'http://attckerserver.local:4000'
  const checks = []
  const check = (name, condition, detail = '') => {
    checks.push({ name, passed: Boolean(condition), detail })
    if (!condition) throw new Error(`check failed: ${name}${detail ? ` (${detail})` : ''}`)
  }

  const healthResponse = await fetch(`${base}/health`)
  const health = await healthResponse.json()
  check('health status', healthResponse.status === 200 && health.status === 'ok' && health.service === 'oast', base)
  check('build id reported', typeof health.buildId === 'string' && health.buildId.length > 0, health.buildId)

  const createdResponse = await fetch(`${base}/api/callbacks`, { method: 'POST' })
  const created = await createdResponse.json()
  check('callback creation', createdResponse.status === 201 && /^[A-Za-z0-9_-]{8,64}$/.test(created.id))
  check('callback URL origin', created.callbackUrl.startsWith(`${base}/c/`), created.callbackUrl)

  const requestBody = 'compose-check-body'
  const callbackResponse = await fetch(`${created.callbackUrl}?probe=compose`, {
    method: 'POST',
    headers: {
      'content-type': 'text/plain',
      'x-oast-compose-check': 'fixture',
    },
    body: requestBody,
  })
  check('callback accepted', callbackResponse.status === 200)

  const list = await (await fetch(`${base}/api/interactions?callbackId=${encodeURIComponent(created.id)}`)).json()
  check('interaction recorded', list.count === 1 && list.total === 1)
  const hit = list.interactions[0]
  check('callback id associated', hit.callbackId === created.id)
  check('method recorded', hit.method === 'POST')
  check('endpoint recorded', hit.endpoint === `/c/${created.id}`)
  check('query recorded', hit.query === '?probe=compose', hit.query)
  check('headers recorded', hit.headers['x-oast-compose-check'] === 'fixture')
  check('body recorded', hit.body === requestBody && hit.bodyBytes === Buffer.byteLength(requestBody))
  check('source address recorded', Boolean(hit.sourceAddress) && hit.sourceAddress !== 'unknown', hit.sourceAddress)
  check('validation recorded', hit.validation === 'accepted')

  const malformed = await fetch(`${base}/c/not-a-valid-id!`)
  check('malformed callback rejected', malformed.status === 400, String(malformed.status))

  const oversized = await fetch(`${base}/c/${'a'.repeat(24)}`, {
    method: 'POST',
    headers: { 'content-type': 'text/plain' },
    body: 'x'.repeat(20 * 1024),
  })
  check('oversized callback rejected', oversized.status === 413, String(oversized.status))

  const dashboard = await fetch(`${base}/`)
  const dashboardHtml = await dashboard.text()
  check('dashboard available', dashboard.status === 200 && dashboardHtml.includes('ElectroMart <span>OAST</span>'))
  check('dashboard shows request details', dashboardHtml.includes('Request data for #') && dashboardHtml.includes(requestBody))

  console.log(JSON.stringify({ status: 'ok', base, checks }, null, 2))
}

main().catch((error) => {
  console.error(JSON.stringify({ status: 'error', message: error.message }))
  process.exit(1)
})
