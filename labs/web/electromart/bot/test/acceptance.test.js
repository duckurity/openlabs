'use strict'

/**
 * Browser acceptance tests for the Phase 2 review-comment link workflow.
 *
 * These tests talk to the real Compose app, create a non-victim review author
 * through the normal registration form, submit reviews through the normal
 * (CSRF-protected) review route, and then run real `runVictimCycle` cycles with
 * Playwright. They are deliberately not unit tests with mocked pages.
 *
 * Run them through `bot/test/run-acceptance.sh` so the persistent bot is paused,
 * the test reviews cannot interfere with it, and the app is reset afterwards.
 */

const test = require('node:test')
const assert = require('node:assert/strict')
const crypto = require('crypto')
const { chromium } = require('playwright')

const { loadConfig } = require('../src/config')
const { makeSanitizer } = require('../src/logger')
const { runVictimCycle, assertPublicHeader } = require('../src/workflow')

const BASE_URL = process.env.ELECTROMART_BASE_URL || 'http://app.test:3000'
const TIMEOUT_MS = Number(process.env.BOT_ACCEPTANCE_TIMEOUT_MS || 20_000)

const PRODUCTS = Object.freeze({
  absolute: 'iphone-17-pro-max',
  relative: 'google-pixel-10-pro',
  external: 'samsung-65-qn70h-neo-qled',
  unsupported: 'samsung-65-u8000h-smart-tv',
  crafted: 'lg-13kg-top-load-washer',
  navigationFailure: 'toshiba-8-5kg-front-load-washer',
  noLink: 'bosch-gas-cooker-5-burners',
  catalogOnly: 'fresh-master-gas-cooker-4',
})

class CookieJar {
  constructor() {
    this.cookies = new Map()
  }

  store(response) {
    const values =
      typeof response.headers.getSetCookie === 'function'
        ? response.headers.getSetCookie()
        : [response.headers.get('set-cookie')].filter(Boolean)
    for (const header of values) {
      const pair = String(header).split(';')[0]
      const equals = pair.indexOf('=')
      if (equals <= 0) continue
      const name = pair.slice(0, equals).trim()
      const value = pair.slice(equals + 1)
      if (value === '') this.cookies.delete(name)
      else this.cookies.set(name, value)
    }
  }

  header() {
    return [...this.cookies.entries()].map(([name, value]) => `${name}=${value}`).join('; ')
  }
}

async function request(jar, requestPath, options = {}) {
  const headers = { ...(options.headers || {}) }
  const cookieHeader = jar.header()
  if (cookieHeader) headers.cookie = cookieHeader
  const response = await fetch(new URL(requestPath, BASE_URL), {
    redirect: 'manual',
    ...options,
    headers,
  })
  jar.store(response)
  return response
}

function extractCsrf(html) {
  const match = String(html).match(/name="csrf_token"\s+value="([^"]+)"/)
  assert.ok(match, 'form did not contain a CSRF token')
  return match[1]
}

function uniqueUsername() {
  return `botlink_${Date.now().toString(36)}_${crypto.randomBytes(3).toString('hex')}`
}

async function registerReviewAuthor() {
  const jar = new CookieJar()
  const password = `Lab-${crypto.randomBytes(18).toString('base64url')}`

  const registerPage = await request(jar, '/register')
  assert.equal(registerPage.status, 200)
  const registerCsrf = extractCsrf(await registerPage.text())

  const body = new URLSearchParams({
    username: uniqueUsername(),
    email: `bot-review-${crypto.randomBytes(6).toString('hex')}@example.test`,
    first_name: 'Review',
    last_name: 'Author',
    password,
    confirm_password: password,
    csrf_token: registerCsrf,
  })
  const registered = await request(jar, '/register', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
  assert.equal(registered.status, 302)
  assert.equal(new URL(registered.headers.get('location'), BASE_URL).pathname, '/home')

  // The authenticated session was regenerated, so read the new CSRF token from
  // an authenticated page rather than reusing the pre-registration token.
  const productPage = await request(jar, `/product/${PRODUCTS.absolute}`)
  assert.equal(productPage.status, 200)
  const csrf = extractCsrf(await productPage.text())

  return { jar, csrf, password }
}

async function postReview(author, slug, comment) {
  const response = await request(author.jar, `/product/${slug}/reviews`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      rating: '5',
      comment,
      csrf_token: author.csrf,
    }).toString(),
  })
  assert.equal(response.status, 302)
  assert.equal(new URL(response.headers.get('location'), BASE_URL).pathname, `/product/${slug}`)
}

function captureLogger() {
  const events = []
  const write = (level) => (event, fields = {}) => {
    events.push({ level, event, ...fields })
  }
  return {
    events,
    logger: {
      debug: write('debug'),
      info: write('info'),
      warn: write('warn'),
      error: write('error'),
      sanitize: makeSanitizer([]),
    },
  }
}

function buildConfig({ slug = null, discover = false } = {}) {
  const { config } = loadConfig({
    ...process.env,
    BOT_PRODUCT_PATHS: discover ? '' : `/product/${slug}`,
    BOT_COMMENT_LINKS_ENABLED: 'true',
    BOT_TIMEOUT_MS: String(TIMEOUT_MS),
    BOT_MAX_RETRIES: '0',
    BOT_READY_TIMEOUT_MS: '60000',
    BOT_LOG_LEVEL: 'debug',
  })
  return config
}

async function runCycle(slug, label, { discover = false } = {}) {
  const cycleId = `accept-${label}-${Date.now().toString(36)}`
  const captured = captureLogger()
  const result = await runVictimCycle({
    config: buildConfig({ slug, discover }),
    logger: captured.logger,
    signal: new AbortController().signal,
    cycleId,
    cycleNumber: 1,
    onResources: () => {},
  })
  return { cycleId, result, events: captured.events }
}

function event(events, name, cycleId) {
  return events.find((entry) => entry.event === name && entry.cycleId === cycleId)
}

function events(eventsList, name, cycleId) {
  return eventsList.filter((entry) => entry.event === name && entry.cycleId === cycleId)
}

test('public login page and public preference route stay unauthenticated', async () => {
  const browser = await chromium.launch({
    headless: true,
    timeout: TIMEOUT_MS,
    args: ['--disable-dev-shm-usage'],
  })
  try {
    const context = await browser.newContext({
      viewport: { width: 1366, height: 900 },
      locale: 'en-GB',
    })
    context.setDefaultTimeout(TIMEOUT_MS)
    context.setDefaultNavigationTimeout(TIMEOUT_MS)
    const page = await context.newPage()

    // Seed the documented promo defaults on the public welcome page.
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' })
    await assertPublicHeader(page, 'public-welcome')

    const seeded = Object.fromEntries(
      (await context.cookies(BASE_URL)).map((cookie) => [cookie.name, cookie.value])
    )
    assert.match(String(seeded.promo_ctx_val), /^\d+$/)

    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' })
    await assertPublicHeader(page, 'public-login')
    assert.equal(await page.locator('.auth-actions').count(), 0)
    assert.equal(await page.locator('#address').count(), 0)

    const loginHtml = await page.content()
    assert.doesNotMatch(loginHtml, /victimEmail@gmail\.com/i)
    assert.doesNotMatch(loginHtml, /delivery address/i)
    assert.doesNotMatch(loginHtml, /duck\{/)

    // This is the app's existing public preference entry point. Review links
    // themselves live on authenticated product pages, so no comment link is
    // reachable while signed out.
    const response = await page.goto(`${BASE_URL}/preferences=phone`, {
      waitUntil: 'domcontentloaded',
    })
    assert.ok(response)
    assert.equal(new URL(page.url()).pathname, '/login')
    await assertPublicHeader(page, 'public-preferences')

    const cookies = Object.fromEntries(
      (await context.cookies(BASE_URL)).map((cookie) => [cookie.name, cookie.value])
    )
    assert.equal(cookies.shop_preferences, 'phone')
    assert.match(String(cookies.promo_ctx_val), /^\d+$/)
    assert.doesNotMatch(await page.content(), /victimEmail@gmail\.com/i)
  } finally {
    await browser.close()
  }
})

test('review-comment link workflow against the real app', { concurrency: false }, async (t) => {
  const author = await registerReviewAuthor()
  const allEvents = []

  await t.test('no qualifying comment link keeps the normal workflow working', async () => {
    const run = await runCycle(PRODUCTS.noLink, 'no-link')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, false)
    assert.equal(run.result.commentLink.reason, 'no-candidates')
    assert.equal(run.result.returnedHome, true)
    assert.equal(run.result.loggedOut, true)
    assert.equal(event(run.events, 'comment_link.selected', run.cycleId), undefined)
    assert.ok(event(run.events, 'welcome.loaded', run.cycleId))
    assert.ok(event(run.events, 'homepage.returned', run.cycleId))
    assert.ok(event(run.events, 'logout.verified', run.cycleId))
    assert.equal(event(run.events, 'logout.verified', run.cycleId).stayedOnWelcome, true)
    const replay = event(run.events, 'login.replay', run.cycleId)
    assert.ok(replay)
    assert.equal(replay.attempted, true)
    assert.equal(replay.succeeded, true)
    assert.equal(replay.outcome, 'succeeded')
    assert.equal(replay.finalPath, '/home')
    assert.equal(run.result.loginReplay.succeeded, true)
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
    assert.equal(
      events(run.events, 'product.verified', run.cycleId)[0].reviewLinks,
      0
    )

    const steps = events(run.events, 'step.ok', run.cycleId).map((entry) => entry.step)
    assert.ok(steps.indexOf('welcome') >= 0)
    assert.ok(steps.indexOf('welcome') < steps.indexOf('login-page'))
    assert.ok(steps.indexOf('login-page') < steps.indexOf('authenticate'))
    assert.ok(steps.indexOf('authenticate') < steps.indexOf('homepage'))
    assert.ok(steps.indexOf('homepage') < steps.indexOf('products'))
    assert.ok(steps.indexOf('products') < steps.indexOf('homepage-return'))
    assert.ok(steps.indexOf('homepage-return') < steps.indexOf('logout'))
    assert.ok(steps.indexOf('logout') < steps.indexOf('login-replay'))
  })

  await t.test('absolute internal comment link is followed and preference verified', async () => {
    await postReview(
      author,
      PRODUCTS.absolute,
      `Please compare ${BASE_URL}/home?preferences=phone before buying.`
    )
    const run = await runCycle(PRODUCTS.absolute, 'absolute')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, true)
    assert.equal(run.result.commentLink.shopPreferences, 'phone')
    assert.equal(run.result.commentLink.homepageObserved, true)
    assert.equal(run.result.commentLink.preferenceOrderOk, true)
    assert.equal(run.result.commentLink.preferenceHintMatches, true)
    assert.equal(run.result.commentLink.promoValueNumeric, true)
    assert.equal(run.result.commentLink.promoValueChanged, false)

    const selected = event(run.events, 'comment_link.selected', run.cycleId)
    assert.equal(selected.path, '/home')
    assert.deepEqual(selected.paramNames, ['preferences'])
    assert.ok(event(run.events, 'comment_link.verified', run.cycleId))
    // The cycle only reaches homepage-return/logout if the authenticated
    // session survived the link navigation.
    assert.ok(event(run.events, 'homepage.returned', run.cycleId))
    assert.ok(event(run.events, 'logout.verified', run.cycleId))
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
  })

  await t.test('relative internal comment link is resolved against the base URL', async () => {
    await postReview(author, PRODUCTS.relative, 'Try /home?preferences=tv for the TV deals.')
    const run = await runCycle(PRODUCTS.relative, 'relative')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, true)
    assert.equal(String(run.result.commentLink.shopPreferences).toLowerCase(), 'tv')
    assert.equal(run.result.commentLink.preferenceOrderOk, true)
    assert.equal(run.result.commentLink.preferenceHintMatches, true)
    const selected = event(run.events, 'comment_link.selected', run.cycleId)
    assert.equal(selected.path, '/home')
    assert.deepEqual(selected.paramNames, ['preferences'])
  })

  await t.test('external comment link is rejected without navigation', async () => {
    await postReview(
      author,
      PRODUCTS.external,
      'See https://example.com/collect?token=not-a-real-token for a better price.'
    )
    const run = await runCycle(PRODUCTS.external, 'external')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, false)
    assert.equal(run.result.commentLink.reason, 'no-eligible-link')
    assert.equal(event(run.events, 'comment_link.selected', run.cycleId), undefined)
    const rejected = event(run.events, 'comment_link.rejected', run.cycleId)
    assert.equal(rejected.reason, 'external-origin')
    assert.equal(rejected.origin, 'https://example.com')
    assert.ok(event(run.events, 'homepage.returned', run.cycleId))
    assert.ok(event(run.events, 'logout.verified', run.cycleId))
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
  })

  await t.test('unsupported scheme is not rendered as a followable comment link', async () => {
    await postReview(
      author,
      PRODUCTS.unsupported,
      'Please never use javascript:alert(1) in a review.'
    )
    const run = await runCycle(PRODUCTS.unsupported, 'unsupported')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, false)
    assert.equal(run.result.commentLink.reason, 'no-candidates')
    assert.equal(event(run.events, 'comment_link.selected', run.cycleId), undefined)
    assert.equal(
      event(run.events, 'product.verified', run.cycleId).reviewLinks,
      0
    )
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
  })

  await t.test('crafted preference input changes promo_ctx but not promo_ctx_val', async () => {
    await postReview(
      author,
      PRODUCTS.crafted,
      `Compare ${BASE_URL}/home?preferences=phone%20promo_ctx=bot_marker safely.`
    )
    const run = await runCycle(PRODUCTS.crafted, 'crafted')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, true)
    assert.equal(run.result.commentLink.craftedPreferenceInput, true)
    assert.equal(run.result.commentLink.shopPreferences, 'phone')
    assert.equal(run.result.commentLink.promoContextChanged, true)
    assert.equal(run.result.commentLink.promoContextPresent, true)
    assert.equal(run.result.commentLink.promoValueNumeric, true)
    assert.equal(run.result.commentLink.promoValueChanged, false)
    assert.equal(run.result.commentLink.preferenceOrderOk, true)

    const observed = event(run.events, 'comment_link.observed', run.cycleId)
    assert.equal(observed.craftedPreferenceInput, true)
    assert.equal(observed.promoContextChanged, true)
    assert.equal(observed.promoValueNumeric, true)
    assert.equal(JSON.stringify(run.events).includes('bot_marker'), false)

    // The crafted cookie survives logout, so the login replay still sees it.
    const replay = event(run.events, 'login.replay', run.cycleId)
    assert.equal(replay.promoContextPresent, true)
    assert.equal(replay.succeeded, true)
  })

  await t.test('failed comment-link navigation is recorded and the browser is closed', async () => {
    await postReview(
      author,
      PRODUCTS.navigationFailure,
      'See /product/this-product-does-not-exist for an example.'
    )
    const run = await runCycle(PRODUCTS.navigationFailure, 'navigation-failure')
    allEvents.push(...run.events)

    assert.equal(run.result.commentLink.followed, false)
    assert.equal(run.result.commentLink.reason, 'http-error')
    assert.equal(run.result.commentLink.status, 404)
    const failed = event(run.events, 'comment_link.navigation-failed', run.cycleId)
    assert.equal(failed.status, 404)
    assert.equal(failed.path, '/product/:slug')
    assert.ok(event(run.events, 'homepage.returned', run.cycleId))
    assert.ok(event(run.events, 'logout.verified', run.cycleId))
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
  })

  await t.test('catalog discovery visits every product, including non-default ones', async () => {
    await postReview(
      author,
      PRODUCTS.catalogOnly,
      `Catalog coverage marker: ${BASE_URL}/home?preferences=phone`
    )
    const run = await runCycle(null, 'catalog-discovery', { discover: true })
    allEvents.push(...run.events)

    assert.equal(run.result.productsVisited, 20)
    assert.ok(run.result.products.includes(`/product/${PRODUCTS.catalogOnly}`))

    const discovered = event(run.events, 'products.discovered', run.cycleId)
    assert.equal(discovered.productCards, 20)
    assert.equal(discovered.productPaths, 20)

    const selected = event(run.events, 'products.selected', run.cycleId)
    assert.equal(selected.source, 'catalog')
    assert.equal(selected.count, 20)

    const verifiedPaths = events(run.events, 'product.verified', run.cycleId).map(
      (entry) => entry.path
    )
    assert.equal(new Set(verifiedPaths).size, 20)
    assert.ok(verifiedPaths.includes(`/product/${PRODUCTS.catalogOnly}`))
    assert.ok(run.result.commentLink.followedCount >= 2)
    assert.ok(
      events(run.events, 'comment_link.selected', run.cycleId).length >= 2,
      'all eligible review links should be followed in one cycle'
    )
    assert.ok(event(run.events, 'homepage.returned', run.cycleId))
    assert.ok(event(run.events, 'logout.verified', run.cycleId))
    assert.ok(event(run.events, 'browser.closed', run.cycleId))
  })

  await t.test('captured logs contain no password, session, flag, or raw cookie values', () => {
    const serialized = JSON.stringify(allEvents)
    assert.equal(serialized.includes(author.password), false)
    assert.equal(serialized.includes('Victim#XSStoAccountTackOver#2'), false)
    assert.equal(serialized.includes('duck{'), false)
    assert.equal(serialized.includes('bot_marker'), false)
    assert.equal(serialized.includes('not-a-real-token'), false)
    assert.doesNotMatch(serialized, /electromart\.sid\s*=/)
    assert.doesNotMatch(serialized, /(?:promo_ctx|promo_ctx_val|shop_preferences)\s*=/)
  })
})
