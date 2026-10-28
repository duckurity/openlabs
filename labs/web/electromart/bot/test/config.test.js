'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')

const { loadConfig, LAB_DEFAULT_VICTIM } = require('../src/config')

test('loadConfig applies safe defaults without exposing the password in the returned shape', () => {
  const { config, warnings } = loadConfig({})
  assert.equal(config.baseUrl, 'http://app.test:3000')
  assert.equal(config.readyPath, '/api/health')
  assert.equal(config.oastBaseUrl, 'http://attckerserver.local:4000')
  assert.equal(config.oastReadyPath, '/health')
  assert.equal(config.xssCheckEnabled, true)
  assert.equal(config.xssCheckTimeoutMs, 15_000)
  assert.equal(config.xssCheckNegativeWaitMs, 2_000)
  assert.equal(config.cycleIntervalMs, 60_000)
  assert.equal(config.timeoutMs, 30_000)
  assert.equal(config.maxRetries, 3)
  assert.equal(config.headless, true)
  assert.equal(config.screenshotsOnFailure, false)
  assert.equal(config.maxCycles, 0)
  assert.equal(config.victim.username, 'victim')
  assert.equal(config.victim.email, LAB_DEFAULT_VICTIM.email)
  assert.equal(config.victim.password, LAB_DEFAULT_VICTIM.password)
  assert.deepEqual(config.productPaths, [])
  assert.equal(config.commentLinksEnabled, true)
  assert.deepEqual(config.allowedLinkOrigins, ['http://app.test:3000'])
  assert.deepEqual(warnings, [])
})

test('loadConfig accepts the documented environment overrides', () => {
  const { config } = loadConfig({
    ELECTROMART_BASE_URL: 'http://shop.internal:3000',
    OAST_BASE_URL: 'http://callbacks.lab.test:4100',
    BOT_XSS_CHECK_ENABLED: 'false',
    BOT_XSS_CHECK_TIMEOUT_MS: '8000',
    BOT_XSS_CHECK_NEGATIVE_WAIT_MS: '700',
    BOT_CYCLE_INTERVAL_MS: '5000',
    BOT_TIMEOUT_MS: '12000',
    BOT_MAX_RETRIES: '1',
    BOT_HEADLESS: 'false',
    BOT_SCREENSHOTS_ON_FAILURE: 'true',
    BOT_PRODUCT_PATHS: '/product/one,/product/two',
    BOT_COMMENT_LINKS_ENABLED: 'false',
    BOT_ALLOWED_LINK_ORIGINS: 'http://app.test:3000,https://lab.test:8443',
    BOT_MAX_CYCLES: '2',
    VICTIM_USERNAME: 'victim',
    VICTIM_EMAIL: 'lab-victim@example.test',
    VICTIM_PASSWORD: 'configured-password',
  })
  assert.equal(config.baseUrl, 'http://shop.internal:3000')
  assert.equal(config.oastBaseUrl, 'http://callbacks.lab.test:4100')
  assert.equal(config.xssCheckEnabled, false)
  assert.equal(config.xssCheckTimeoutMs, 8000)
  assert.equal(config.xssCheckNegativeWaitMs, 700)
  assert.equal(config.cycleIntervalMs, 5000)
  assert.equal(config.timeoutMs, 12000)
  assert.equal(config.maxRetries, 1)
  assert.equal(config.headless, false)
  assert.equal(config.screenshotsOnFailure, true)
  assert.deepEqual(config.productPaths, ['/product/one', '/product/two'])
  assert.equal(config.commentLinksEnabled, false)
  assert.deepEqual(config.allowedLinkOrigins, [
    'http://shop.internal:3000',
    'http://app.test:3000',
    'https://lab.test:8443',
  ])
  assert.equal(config.maxCycles, 2)
  assert.equal(config.victim.email, 'lab-victim@example.test')
  assert.equal(config.victim.password, 'configured-password')
})

test('loadConfig rejects credentials or malformed base URLs', () => {
  assert.throws(() => loadConfig({ ELECTROMART_BASE_URL: 'ftp://app:3000' }), /http/)
  assert.throws(() => loadConfig({ ELECTROMART_BASE_URL: 'not a url' }), /valid URL/)
  assert.throws(
    () => loadConfig({ ELECTROMART_BASE_URL: 'http://user:pass@app:3000' }),
    /credentials/
  )
  assert.throws(() => loadConfig({ OAST_BASE_URL: 'ftp://oast:4000' }), /OAST_BASE_URL.*http/)
  assert.throws(
    () => loadConfig({ OAST_BASE_URL: 'http://user:pass@oast:4000' }),
    /OAST_BASE_URL.*credentials/
  )
})

test('loadConfig drops unsafe product paths and falls back to catalog discovery', () => {
  const first = loadConfig({ BOT_PRODUCT_PATHS: 'https://evil.test/x, /product/ok' })
  assert.deepEqual(first.config.productPaths, ['/product/ok'])
  assert.ok(first.warnings.some((warning) => warning.includes('evil.test')))

  const second = loadConfig({ BOT_PRODUCT_PATHS: '//evil.test/x' })
  assert.deepEqual(second.config.productPaths, [])
  assert.ok(second.warnings.some((warning) => warning.includes('catalog discovery')))

  const empty = loadConfig({ BOT_PRODUCT_PATHS: '' })
  assert.deepEqual(empty.config.productPaths, [])
  assert.deepEqual(empty.warnings, [])
})

test('loadConfig ignores malformed or credential-bearing link origins', () => {
  const { config, warnings } = loadConfig({
    BOT_ALLOWED_LINK_ORIGINS: 'ftp://lab.test,http://user:pass@lab.test,not a url',
  })
  assert.deepEqual(config.allowedLinkOrigins, ['http://app.test:3000'])
  assert.equal(warnings.filter((warning) => warning.includes('BOT_ALLOWED_LINK_ORIGINS')).length, 3)
})

test('loadConfig treats an empty VICTIM_PASSWORD as the documented lab default', () => {
  const { config } = loadConfig({ VICTIM_PASSWORD: '' })
  assert.equal(config.victim.password, LAB_DEFAULT_VICTIM.password)
})
