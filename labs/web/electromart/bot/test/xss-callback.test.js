'use strict'

/**
 * End-to-end Phase 3 verification (Tests C and D).
 *
 * Requires the Compose stack (app + OAST). It runs the same isolated validation
 * used by the bot at startup: fresh browser context, synthetic preference
 * value, harmless proof-of-execution marker, and a negative control that proves
 * a plain page visit is not reported as XSS.
 *
 * Run inside the bot network:
 *   docker compose run --rm --no-deps --entrypoint node bot --test test/xss-callback.test.js
 * or with the default bot image command:
 *   docker compose exec bot node --test test/xss-callback.test.js
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const { loadConfig } = require('../src/config')
const { createLogger } = require('../src/logger')
const { runOastXssValidation } = require('../src/xss-check')

const events = []

function capturingLogger(level = 'debug') {
  const logger = createLogger({ level })
  return {
    debug: (event, meta) => { events.push({ event, meta }); logger.debug(event, meta) },
    info: (event, meta) => { events.push({ event, meta }); logger.info(event, meta) },
    warn: (event, meta) => { events.push({ event, meta }); logger.warn(event, meta) },
    error: (event, meta) => { events.push({ event, meta }); logger.error(event, meta) },
    sanitize: logger.sanitize,
  }
}

test('Test C/D: XSS marker reaches OAST, negative control is clean, cookies behave', { timeout: 90_000 }, async () => {
  const { config, warnings } = loadConfig({
    ...process.env,
    BOT_XSS_CHECK_ENABLED: 'true',
    BOT_XSS_CHECK_TIMEOUT_MS: process.env.BOT_XSS_CHECK_TIMEOUT_MS || '20000',
    BOT_XSS_CHECK_NEGATIVE_WAIT_MS: process.env.BOT_XSS_CHECK_NEGATIVE_WAIT_MS || '1500',
  })
  assert.deepEqual(warnings.filter((warning) => !warning.includes('BOT_MAX_CYCLES')), [])

  const logger = capturingLogger()
  const result = await runOastXssValidation({
    config,
    logger,
    signal: new AbortController().signal,
    cycleId: `test-${Date.now().toString(36)}`,
  })

  assert.ok(result.callbackId)
  assert.equal(result.method, 'GET')
  assert.equal(result.endpoint, `/c/${result.callbackId}`)
  assert.equal(result.validation, 'accepted')
  assert.ok(result.sourceAddress && result.sourceAddress !== 'unknown')
  assert.equal(result.negativeControlClean, true)
  assert.equal(result.loginRequestCookieSent, true)
  assert.equal(result.cookieFlow.promoCtxPresent, true)
  assert.equal(result.cookieFlow.promoCtxIsDefault, true)
  assert.equal(result.cookieFlow.promoCtxUpdated, true)
  assert.equal(result.cookieFlow.promoValNumeric, true)
  assert.equal(result.cookieFlow.promoValUnchanged, true)
  assert.equal(result.cookieFlow.promoValStillNumeric, true)

  // The interaction is queryable afterwards, not just a transient browser state.
  const response = await fetch(
    `${config.oastBaseUrl}/api/interactions?callbackId=${encodeURIComponent(result.callbackId)}`
  )
  assert.equal(response.status, 200)
  const payload = await response.json()
  assert.equal(payload.total, 1)
  assert.equal(payload.interactions[0].callbackId, result.callbackId)

  // No credential, cookie value, or marker text may reach the logs.
  const serialized = JSON.stringify(events)
  assert.equal(serialized.includes(config.victim.password), false)
  assert.doesNotMatch(serialized, /promo_ctx=(?!\[redacted\])/)
  assert.equal(serialized.includes('location='), false)
})
