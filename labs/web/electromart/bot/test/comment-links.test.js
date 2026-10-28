'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')

const {
  validateCommentLink,
  selectCommentLink,
  labPathLabel,
} = require('../src/comment-links')

const BASE = 'http://app.test:3000'
const ORIGINS = ['http://app.test:3000']

test('relative comment links resolve against the configured base URL', () => {
  const result = validateCommentLink({
    href: '/home?preferences=phone',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(result.ok, true)
  assert.equal(result.origin, BASE)
  assert.equal(result.pathname, '/home')
  assert.equal(result.pathLabel, '/home')
  assert.deepEqual(result.paramNames, ['preferences'])
  assert.equal(result.url, `${BASE}/home?preferences=phone`)
})

test('absolute links are accepted only on an allowed origin', () => {
  const sameOrigin = validateCommentLink({
    href: `${BASE}/preferences=tv`,
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(sameOrigin.ok, true)
  assert.equal(sameOrigin.pathLabel, '/preferences=:value')

  const allowlisted = validateCommentLink({
    href: 'https://lab.test:8443/home',
    baseUrl: BASE,
    allowedOrigins: [...ORIGINS, 'https://lab.test:8443'],
  })
  assert.equal(allowlisted.ok, true)

  const external = validateCommentLink({
    href: 'https://evil.test/home?preferences=phone',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(external.ok, false)
  assert.equal(external.reason, 'external-origin')
  assert.equal(external.origin, 'https://evil.test')
})

test('unsupported schemes, credential URLs, and out-of-scope paths are rejected', () => {
  for (const href of [
    'javascript:alert(1)',
    'data:text/html,<b>x</b>',
    'mailto:test@example.com',
    'file:///etc/passwd',
  ]) {
    const result = validateCommentLink({ href, baseUrl: BASE, allowedOrigins: ORIGINS })
    assert.equal(result.ok, false, href)
    assert.equal(result.reason, 'unsupported-scheme', href)
  }

  const credentials = validateCommentLink({
    href: 'http://user:pass@app.test:3000/home',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(credentials.ok, false)
  assert.equal(credentials.reason, 'credentials-in-url')

  const profile = validateCommentLink({
    href: '/profile',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(profile.ok, false)
  assert.equal(profile.reason, 'outside-lab-scope')

  const health = validateCommentLink({
    href: '/api/health',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(health.ok, false)
  assert.equal(health.reason, 'outside-lab-scope')

  const welcome = validateCommentLink({
    href: '/',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(welcome.ok, false)
  assert.equal(welcome.reason, 'outside-lab-scope')
})

test('protocol-relative and duplicate links are rejected', () => {
  const protocolRelative = validateCommentLink({
    href: '//evil.test/home',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(protocolRelative.ok, false)
  assert.equal(protocolRelative.reason, 'external-origin')

  const first = validateCommentLink({
    href: '/home?preferences=phone',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  const duplicate = validateCommentLink({
    href: '/home?preferences=phone',
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
    visitedUrls: new Set([first.key]),
  })
  assert.equal(duplicate.ok, false)
  assert.equal(duplicate.reason, 'duplicate-link')
})

test('selection returns a safe path label and never copies hrefs into rejections', () => {
  const result = selectCommentLink({
    candidates: [
      { href: 'https://evil.test/secret?token=abc', productPath: '/product/a' },
      { href: '/home?preferences=phone promo_ctx=bot_marker', productPath: '/product/b' },
    ],
    baseUrl: BASE,
    allowedOrigins: ORIGINS,
  })
  assert.equal(result.selected.pathLabel, '/home')
  assert.deepEqual(result.selected.paramNames, ['preferences'])
  assert.equal(result.selected.sourceProductPath, '/product/b')
  assert.equal(result.rejected.length, 1)
  assert.equal(result.rejected[0].reason, 'external-origin')
  assert.equal(result.rejected[0].origin, 'https://evil.test')
  assert.equal(JSON.stringify(result.rejected).includes('token=abc'), false)
  assert.equal(JSON.stringify(result.rejected).includes('secret'), false)
})

test('path labels redact preference values', () => {
  assert.equal(labPathLabel('/preferences=phone'), '/preferences=:value')
  assert.equal(labPathLabel('/product/samsung-galaxy-s25-ultra'), '/product/:slug')
  assert.equal(labPathLabel('/home/'), '/home')
  assert.equal(labPathLabel('/api/health'), null)
})
