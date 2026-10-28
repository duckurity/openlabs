'use strict'

/**
 * ============================================================
 *  Phase 1.3 — BROWSER / HTTP-LEVEL ACCEPTANCE TESTS (Section 6)
 * ============================================================
 *  Verifies the cookie-state requirements end to end against the
 *  LIVE application (real HTTP, real Cookie / Set-Cookie headers,
 *  a faithful browser cookie jar). These prove behaviour at the
 *  wire — not merely that a URL "contains" expected text.
 *
 *  Requires the stack to be up:  `docker compose up -d --build`
 *  (or set APP_URL). No third-party dependencies.
 *
 *  NOTE on the lab's "preferences" entry point: the application's
 *  legitimate preference-selection mechanism is `GET /preferences=:value`
 *  (there is no /home?preferences= parameter). This file exercises that
 *  canonical mechanism, and also the product-detail path which updates
 *  shop_preferences by browsing a real product.
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const BASE = process.env.APP_URL || 'http://localhost:3000'
const VICTIM_USER = 'victim'
const VICTIM_PASS = 'Victim#XSStoAccountTackOver#2'

/**
 * Harmless, isolated proof-of-execution payload.
 *
 * It contains NO internal spaces (the documented parser splits each cookie
 * pair on internal whitespace, so a space-free value is smuggled verbatim)
 * and NO double quotes (the value is reflected into a double-quoted JS
 * string, `promoContext: "..."`, and both the render and this test read up
 * to the first unescaped `"`). It is intentionally harmless: it can only
 * pop an alert on the two designated lab sinks, exfiltrate nothing, and
 * capture no credentials.
 */
const PAYLOAD = '<script>alert(1)</script>'

/** Lab cookie names (see src/utils/promo.js). */
const LAB_COOKIE_NAMES = ['shop_preferences', 'promo_ctx', 'promo_ctx_val']

/**
 * Minimal cookie jar mirroring how a browser stores/sends cookies. Values are
 * held raw (exactly as the server serialised them, i.e. percent-encoded); a
 * browser stores the raw value and sends it back raw, so toHeader() re-encodes
 * nothing. get() returns the DECODED value (what the value means) for clean
 * assertions.
 */
class Jar {
  constructor() { this.map = new Map() }
  absorb(header) {
    if (!header) return
    for (let part of header.split(';')) {
      part = part.trim()
      if (!part) continue
      const i = part.indexOf('=')
      if (i > 0) this.map.set(part.slice(0, i), part.slice(i + 1))
    }
  }
  toHeader() { return [...this.map.entries()].map(([k, v]) => `${k}=${v}`).join('; ') }
  raw(name) { return this.map.get(name) }
  get(name) {
    const v = this.map.get(name)
    if (v === undefined) return undefined
    try { return decodeURIComponent(v) } catch { return v }
  }
  has(name) { return this.map.has(name) }
  names() { return [...this.map.keys()] }
  clear() { this.map.clear() }
}

/**
 * Merge the jar's stored cookies with an optional explicit `Cookie` header
 * string. Mirrors the proven `integration.test.js` harness: when an explicit
 * (crafted) header is supplied, it is authoritative for the LAB cookies — the
 * jar's possibly-stale lab copies are dropped so the crafted value is the only
 * one on the wire. The session cookie (and any non-lab cookie) is always kept.
 */
function mergeCookies(jar, explicitCookie) {
  const names = new Set()
  const out = []
  if (explicitCookie) {
    for (const part of String(explicitCookie).split(';')) {
      const p = part.trim()
      if (!p) continue
      const i = p.indexOf('=')
      const name = i > 0 ? p.slice(0, i) : p
      names.add(name)
      out.push(p)
    }
  }
  if (jar) {
    for (const [name, value] of jar.map.entries()) {
      if (names.has(name)) continue
      if (explicitCookie && LAB_COOKIE_NAMES.includes(name)) continue // drop stale lab cookies
      out.push(name + '=' + value)
    }
  }
  return out.length ? out.join('; ') : undefined
}

/**
 * Perform a fetch, updating `jar` with any Set-Cookie. The normal browser
 * mechanism is used throughout: the jar sends its stored cookies back in the
 * `Cookie` request header. An OPTIONAL explicit `Cookie` string (e.g. the
 * crafted malformed lab input) becomes authoritative for the lab cookies.
 */
async function doFetch(url, { jar, headers = {}, method = 'GET', redirect = 'follow', body } = {}) {
  const cookie = mergeCookies(jar, headers.Cookie)
  const res = await fetch(BASE + url, {
    method,
    redirect,
    headers: {
      ...(cookie ? { Cookie: cookie } : {}),
      ...(body ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}),
    },
    body: body ? body.toString() : undefined,
  })
  if (jar) for (const sc of (res.headers.getSetCookie() || [])) jar.absorb(sc)
  const text = await res.text()
  return { status: res.status, headers: res.headers, body: text, location: res.headers.get('location') }
}

/** Set-Cookie names emitted by a response (value part stripped of attrs). */
function setCookieNames(res) {
  return (res.headers.getSetCookie() || []).map((h) => h.split(';')[0])
}

/** Extract the inline window.electroMart object from a page. */
function extractElectroMart(html) {
  const ctx = /promoContext:\s*"((?:\\.|[^"\\])*)"/.exec(html)
  const val = /promoValue:\s*(\d+)/.exec(html)
  return {
    present: /window\.electroMart\s*=/.test(html),
    promoContext: ctx ? ctx[1] : null,
    promoValue: val ? Number(val[1]) : null,
  }
}

/** Log in as a known user; returns an authenticated jar (+ the raw response). */
async function loginAs(username, password) {
  const jar = new Jar()
  const page = await doFetch('/login', { jar })
  const csrf = /name="csrf_token" value="([^"]+)"/.exec(page.body)?.[1]
  const res = await doFetch('/login', {
    jar,
    method: 'POST',
    redirect: 'manual',
    body: new URLSearchParams({ username, password, csrf_token: csrf }),
  })
  return { jar, res, csrf }
}

function readCsrf(html) { return /name="csrf_token" value="([^"]+)"/.exec(html)?.[1] }

// ============================================================
//  TEST A — Initial Cookie Creation (Requirement 1)
// ============================================================

test('A: first Welcome Page visit initializes promo_ctx + promo_ctx_val via Set-Cookie', async () => {
  const jar = new Jar()
  const res = await doFetch('/', { jar })
  assert.equal(res.status, 200)
  const names = setCookieNames(res)
  assert.ok(
    names.some((n) => n.startsWith('promo_ctx=summer_sale')),
    `welcome response must Set-Cookie promo_ctx=summer_sale (saw: ${JSON.stringify(names)})`
  )
  assert.ok(
    names.some((n) => n.startsWith('promo_ctx_val=30')),
    `welcome response must Set-Cookie promo_ctx_val=30 (saw: ${JSON.stringify(names)})`
  )
  // The welcome page never renders either value.
  assert.ok(!res.body.includes('summer_sale'), 'welcome body must NOT render promo_ctx')
  assert.ok(!/promo_ctx_val|Up to \d+% off/.test(res.body) || !res.body.includes('summer_sale'),
    'welcome body must NOT render the promo value')
  // Cookies were stored by the (simulated) browser.
  assert.equal(jar.get('promo_ctx'), 'summer_sale')
  assert.equal(jar.get('promo_ctx_val'), '30')
})

test('A: a returning welcome visit (cookies already sent) does NOT reissue the defaults', async () => {
  const jar = new Jar()
  jar.absorb('promo_ctx=summer_sale; promo_ctx_val=30; shop_preferences=none')
  const res = await doFetch('/', { jar })
  const names = setCookieNames(res)
  assert.ok(!names.some((n) => n.startsWith('promo_ctx=')),
    `must not reissue promo_ctx when already present (saw: ${JSON.stringify(names)})`)
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')),
    `must not reissue promo_ctx_val when already present (saw: ${JSON.stringify(names)})`)
})

test('A: an intentional lab-state change is NOT reset on the next welcome visit', async () => {
  const jar = new Jar()
  // Browser already holds a crafted promo_ctx from the lab (req 1, item 3).
  jar.absorb('promo_ctx=' + encodeURIComponent(PAYLOAD) + '; promo_ctx_val=30; shop_preferences=phone')
  const res = await doFetch('/', { jar })
  const names = setCookieNames(res)
  assert.ok(!names.some((n) => n.startsWith('promo_ctx=')),
    `an existing (lab-state) promo_ctx must NOT be overwritten (saw: ${JSON.stringify(names)})`)
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')),
    `an existing promo_ctx_val must NOT be overwritten (saw: ${JSON.stringify(names)})`)
  // The stored (non-default) value was preserved, not reset to summer_sale.
  assert.equal(jar.get('promo_ctx'), PAYLOAD)
})

test('A: promo cookies are scoped to path=/ (usable site-wide)', async () => {
  const res = await doFetch('/')
  const ctx = (res.headers.getSetCookie() || []).find((h) => h.startsWith('promo_ctx='))
  assert.ok(/(; )Path=\/(; |$)/.test(ctx), `promo_ctx carries Path=/ (saw: ${ctx})`)
})

// ============================================================
//  TEST B — Cookie Persistence (Requirement 2)
// ============================================================

test('B: Login Page reads the stored promo_ctx / promo_ctx_val from the browser (fresh-visit defaults)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar }) // welcome -> stored defaults
  const res = await doFetch('/login', { jar })
  assert.equal(res.status, 200)
  const em = extractElectroMart(res.body)
  assert.ok(em.present, 'login renders window.electroMart (JS sink)')
  // Rendered values must equal the values the BROWSER SENT (the jar), so this
  // also fails if the server read anything other than the request cookies.
  assert.equal(em.promoContext, jar.get('promo_ctx'), 'login uses the STORED promo_ctx')
  assert.equal(em.promoValue, Number(jar.get('promo_ctx_val')), 'login uses the STORED promo_ctx_val')
})

/**
 * DISCRIMINATING persistence check: the stored (browser) values below are
 * DELIBERATELY different from the defaults ("summer_sale"/30). If the page
 * hard-coded template values or constants instead of reading the request
 * cookies, these assertions would fail — so this proves the server actually
 * consumes the promo cookies the browser sends (req 2, "sent and read").
 */
test('B: a NON-default stored promo value is exactly what the Login Page renders', async () => {
  const jar = new Jar()
  await doFetch('/', { jar }) // first-visit init: the browser now holds the cookies
  // Stored lab state the browser carries on the next request (non-default pair).
  jar.absorb('promo_ctx=winter_sale; promo_ctx_val=45')
  const res = await doFetch('/login', { jar })
  assert.equal(res.status, 200)
  const em = extractElectroMart(res.body)
  assert.ok(em.present, 'login renders window.electroMart (JS sink)')
  assert.equal(em.promoContext, 'winter_sale', 'login renders the STORED non-default promo_ctx (not a hardcoded value)')
  assert.equal(em.promoValue, 45, 'login renders the STORED non-default promo_ctx_val (not the 30 default)')
  // The visible banner must consume the same value as Home — not the clamped
  // safe title ("Winter Sale"), which would hide an arbitrary lab value.
  assert.ok(res.body.includes('Check out the winter_sale'),
    'login banner reflects the stored promo_ctx verbatim (same as Home)')
  assert.ok(!res.body.includes('Check out the Winter Sale'),
    'login banner must not clamp the value to the safe title')
})

test('B: the Login banner shows an arbitrary stored promo_ctx (e.g. "hello")', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  jar.absorb('promo_ctx=hello')
  const res = await doFetch('/login', { jar })
  assert.equal(res.status, 200)
  assert.ok(res.body.includes('Check out the hello'),
    'login banner reflects an arbitrary stored promo_ctx verbatim')
  assert.ok(!res.body.includes('Check out the Summer Sale'),
    'login banner must not fall back to the Summer Sale title')
})

test('B: the authenticated Home Page reads the stored (non-default) promo values from the browser', async () => {
  const jar = new Jar()
  await doFetch('/', { jar }) // welcome -> stored defaults
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  // The browser (victim's session + promo cookies) carries a non-default pair.
  authJar.absorb('promo_ctx=black_friday; promo_ctx_val=25')
  const res = await doFetch('/home', { jar: authJar })
  assert.equal(res.status, 200)
  const em = extractElectroMart(res.body)
  assert.ok(em.present, 'home renders window.electroMart (JS sink)')
  assert.equal(em.promoContext, 'black_friday', 'home renders the STORED non-default promo_ctx sent by the browser')
  assert.equal(em.promoValue, 25, 'home renders the STORED non-default promo_ctx_val')
})

test('B: an intentional lab-state change (crafted promo_ctx) is consumed, not reset', async () => {
  const jar = new Jar()
  await doFetch('/', { jar }) // init
  // Simulate the browser having picked up a crafted promo_ctx (from a prior lab step).
  jar.absorb('promo_ctx=' + encodeURIComponent(PAYLOAD) + '; promo_ctx_val=30; shop_preferences=phone')
  const res = await doFetch('/login', { jar })
  const em = extractElectroMart(res.body)
  assert.equal(em.promoContext, PAYLOAD, 'login consumes the STORED crafted promo_ctx')
  assert.equal(em.promoValue, 30, 'promo_ctx_val stays the numeric 30')
})

// ============================================================
//  TEST C — Preference behaviour (shop_preferences + ordering)
// ============================================================

function slugsFromHome(html) {
  const out = []
  const re = /href="\/product\/([^"]+)"/g
  let m
  while ((m = re.exec(html)) !== null) out.push(m[1])
  return out
}
/**
 * Assert a preferred-category-first ordering: the list must be a permutation
 * of all products, and EVERY phone product must appear before the first
 * non-phone product. (The preferred category is a sorted prefix of the same
 * category-filtered set, so comparing sorted prefixes proves the reordering
 * without depending on the two queries returning identical sort orders.)
 */
function assertPreferredFirst(orderedSlugs, preferredSlugs) {
  const preferred = new Set(preferredSlugs)
  let seenOther = false
  for (const s of orderedSlugs) {
    if (preferred.has(s)) assert.ok(!seenOther, 'a preferred product appears after a non-preferred one (not preferred-first)')
    else seenOther = true
  }
  assert.equal(new Set(orderedSlugs).size, orderedSlugs.length, 'no duplicate products')
  const preferredInOrder = orderedSlugs.filter((s) => preferred.has(s))
  assert.equal(preferredInOrder.length, preferredSlugs.length, 'preferred category count preserved (nothing hidden)')
  assert.deepEqual([...preferredInOrder].sort(), [...preferredSlugs].sort(), 'preferred products are all present')
}

test('C: visiting a valid phone product updates shop_preferences to "phone"', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  authJar.absorb('shop_preferences=none')
  // Find a phone product slug via the category filter, then browse it.
  const phoneList = await doFetch('/home?category=phone', { jar: authJar })
  const slugs = slugsFromHome(phoneList.body)
  assert.ok(slugs.length > 0, 'there are phone products')
  const detail = await doFetch('/product/' + slugs[0], { jar: authJar })
  assert.equal(detail.status, 200)
  const names = setCookieNames(detail)
  assert.ok(names.some((n) => n === 'shop_preferences=phone'),
    `visiting a phone product sets shop_preferences=phone (saw: ${JSON.stringify(names)})`)
  assert.equal(authJar.get('shop_preferences'), 'phone')
})

test('C: unfiltered homepage prioritizes the preferred (phone) category', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const phones = slugsFromHome((await doFetch('/home?category=phone', { jar: authJar })).body)
  const pref = slugsFromHome(
    (await doFetch('/home', { jar: authJar, headers: { Cookie: 'shop_preferences=phone' } })).body
  )
  assertPreferredFirst(pref, phones)
})

test('C: browsing a phone product, then returning home, prioritizes phones via the browser jar (no forged headers)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  authJar.absorb('shop_preferences=none')
  // Open a valid phone product (server sets shop_preferences=phone).
  const phoneList = await doFetch('/home?category=phone', { jar: authJar })
  const phoneSlugs = slugsFromHome(phoneList.body)
  assert.ok(phoneSlugs.length > 0, 'phone products exist')
  const detail = await doFetch('/product/' + phoneSlugs[0], { jar: authJar })
  assert.equal(detail.status, 200)
  assert.ok(setCookieNames(detail).some((n) => n === 'shop_preferences=phone'),
    'product-detail response Set-Cookie: shop_preferences=phone')
  assert.equal(authJar.get('shop_preferences'), 'phone')
  // Return to the UNFILTERED homepage sending EXACTLY what the browser now
  // stores (normal cookie mechanism, no explicit header).
  const home = await doFetch('/home', { jar: authJar })
  const ordered = slugsFromHome(home.body)
  assertPreferredFirst(ordered, phoneSlugs)
  assert.ok(home.body.includes('Showing <strong>phone</strong> products first'),
    'home shows the preference hint for the stored value')
})

test('C: the /preferences=:value mechanism sets shop_preferences and reorders the home', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  // The app's legitimate preference-selection URL form.
  const set = await doFetch('/preferences=phone', { jar: authJar, redirect: 'manual' })
  assert.equal(set.status, 302)
  assert.equal(set.location, '/home')
  assert.ok(setCookieNames(set).some((n) => n === 'shop_preferences=phone'),
    'response sets shop_preferences=phone')
  // Using the browser-stored value now orders phones first.
  const page = await doFetch('/home', { jar: authJar })
  const phones = slugsFromHome((await doFetch('/home?category=phone', { jar: authJar })).body)
  assertPreferredFirst(slugsFromHome(page.body), phones)
})

test('C: GET /home?preferences=phone sets the real cookie and orders phones first (browser jar only)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  // No explicit Cookie header: the jar behaves like a normal browser.
  const page = await doFetch('/home?preferences=phone', { jar: authJar })
  assert.equal(page.status, 200)
  assert.ok(setCookieNames(page).some((n) => n === 'shop_preferences=phone'),
    'home preference parameter emits Set-Cookie: shop_preferences=phone')
  assert.equal(authJar.get('shop_preferences'), 'phone', 'browser stored shop_preferences=phone')
  const phones = slugsFromHome((await doFetch('/home?category=phone', { jar: authJar })).body)
  assertPreferredFirst(slugsFromHome(page.body), phones)
  // The next plain homepage request uses the stored preference.
  const next = await doFetch('/home', { jar: authJar })
  assertPreferredFirst(slugsFromHome(next.body), phones)
  assert.ok(next.body.includes('Showing <strong>phone</strong> products first'))
})

test('C: GET /home?preferences=washing machine stores the full multi-word preference', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const url = '/home?' + new URLSearchParams({ preferences: 'washing machine' }).toString()
  const page = await doFetch(url, { jar: authJar })
  assert.ok(setCookieNames(page).some((n) => n === 'shop_preferences=washing%20machine' || n === 'shop_preferences=washing machine'),
    'multi-word preference is preserved')
  assert.equal(authJar.get('shop_preferences'), 'washing machine')
  const washers = slugsFromHome((await doFetch('/home?category=washing%20machine', { jar: authJar })).body)
  assertPreferredFirst(slugsFromHome((await doFetch('/home', { jar: authJar })).body), washers)
})

// ============================================================
//  TEST D — Intended cookie-parsing interaction (the lab flaw)
// ============================================================

test('D: crafted ?preferences= URL drives the promo_ctx state transition (browser jar only)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar }) // welcome -> stored defaults
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  await doFetch('/', { jar: authJar }) // ensure the browser holds the default promo pair
  assert.equal(authJar.get('promo_ctx'), 'summer_sale')
  assert.equal(authJar.get('promo_ctx_val'), '30')

  // The documented malformed input is ONE query value: a legitimate preference
  // followed by a SPACE and an embedded promo_ctx assignment. A space does NOT
  // delimit query parameters, so this is exactly what the server receives.
  const craftedValue = 'phone promo_ctx=' + PAYLOAD
  const craftedUrl = '/home?' + new URLSearchParams({ preferences: craftedValue }).toString()
  const res = await doFetch(craftedUrl, { jar: authJar }) // normal browser cookie flow
  assert.equal(res.status, 200)
  // The crafted value must be visible immediately in THIS response, matching
  // the Set-Cookie the browser is about to store (no reload required).
  assert.ok(res.body.includes(`promo-banner__name">${PAYLOAD}</span>`),
    'the crafted response banner renders the injected promo_ctx immediately')

  const names = setCookieNames(res)
  // 1) The response re-issued promo_ctx with the injected value (state change).
  const injectedCookie = names.find((n) => n.startsWith('promo_ctx='))
  assert.ok(injectedCookie,
    `the crafted input MUST re-issue Set-Cookie promo_ctx (saw: ${JSON.stringify(names)})`)
  assert.equal(decodeURIComponent(injectedCookie.split('=')[1]), PAYLOAD,
    'the re-issued promo_ctx value is the attacker payload (cookie state transition)')
  assert.ok(names.some((n) => n === 'shop_preferences=phone'), 'shop_preferences is still the valid phone category')
  // 2) promo_ctx_val was NOT touched — the crafted input cannot change it.
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')),
    `promo_ctx_val must NOT be re-issued by the crafted input (saw: ${JSON.stringify(names)})`)

  // 3) The browser now STORES the updated value (jar processed Set-Cookie).
  assert.equal(authJar.get('promo_ctx'), PAYLOAD, 'stored promo_ctx is the payload')
  assert.equal(authJar.get('promo_ctx_val'), '30', 'stored promo_ctx_val is unchanged (30)')

  // 4) On a SUBSEQUENT request the server reads and renders the stored value.
  const home = await doFetch('/home', { jar: authJar })
  const em = extractElectroMart(home.body)
  assert.equal(em.promoContext, PAYLOAD, 'next request consumes the stored promo_ctx (payload)')
  assert.equal(em.promoValue, 30, 'next request still reads promo_ctx_val=30 (separate + validated)')

  // 5) A clean preference update must not reset the lab state or re-issue promo_ctx.
  const clean = await doFetch('/home?preferences=tv', { jar: authJar })
  assert.ok(!setCookieNames(clean).some((n) => n.startsWith('promo_ctx=')),
    'an ordinary (clean) preference update does not re-issue promo_ctx')
  assert.equal(authJar.get('promo_ctx'), PAYLOAD, 'clean preference update did not undo the lab-state change')
})

test('D: crafted preference input cannot modify promo_ctx_val even when it embeds one', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  await doFetch('/', { jar: authJar })
  const craftedValue = 'phone promo_ctx=' + PAYLOAD + ' promo_ctx_val=99'
  const craftedUrl = '/home?' + new URLSearchParams({ preferences: craftedValue }).toString()
  const res = await doFetch(craftedUrl, { jar: authJar })
  const names = setCookieNames(res)
  assert.ok(names.some((n) => n.startsWith('promo_ctx=')), 'promo_ctx transition still fires')
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')),
    `embedded promo_ctx_val must be ignored (saw: ${JSON.stringify(names)})`)
  assert.equal(authJar.get('promo_ctx_val'), '30', 'browser promo_ctx_val remained 30')
  const home = await doFetch('/home', { jar: authJar })
  assert.equal(extractElectroMart(home.body).promoValue, 30, 'rendered discount remained 30')
})

test('D: the legacy /preferences=<crafted> route also transitions promo_ctx via the browser jar', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  await doFetch('/', { jar: authJar })
  const craftedValue = 'phone promo_ctx=' + PAYLOAD
  const res = await doFetch('/preferences=' + encodeURIComponent(craftedValue), {
    jar: authJar, redirect: 'manual',
  })
  assert.equal(res.status, 302)
  const names = setCookieNames(res)
  const injected = names.find((n) => n.startsWith('promo_ctx='))
  assert.ok(injected, `legacy preference route re-issues promo_ctx (saw: ${JSON.stringify(names)})`)
  assert.equal(decodeURIComponent(injected.split('=')[1]), PAYLOAD)
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')), 'promo_ctx_val untouched')
  assert.equal(authJar.get('promo_ctx'), PAYLOAD, 'browser stored the injected promo_ctx')
  assert.equal(authJar.get('promo_ctx_val'), '30', 'browser promo_ctx_val unchanged')
})

test('D: a clean (non-crafted) preference update does NOT trigger the transition', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const res = await doFetch('/preferences=phone', { jar, redirect: 'manual' })
  const names = setCookieNames(res)
  assert.ok(names.some((n) => n === 'shop_preferences=phone'), 'normal preference set')
  assert.ok(!names.some((n) => n.startsWith('promo_ctx=')), 'no promo_ctx re-issue for clean input')
  assert.ok(!names.some((n) => n.startsWith('promo_ctx_val=')), 'no promo_ctx_val re-issue for clean input')
  // The stored default stays summer_sale (not clobbered).
  assert.equal(jar.get('promo_ctx'), 'summer_sale')
})

// ============================================================
//  TEST E — Reflected-XSS verification (harmless, isolated payload)
// ============================================================

test('E: the designated Login sink reflects the crafted promo_ctx (no contextual escaping)', async () => {
  const jar = new Jar()
  // Force the lab browser state to hold the crafted value, then load /login.
  jar.absorb('promo_ctx=' + encodeURIComponent(PAYLOAD) + '; promo_ctx_val=30; shop_preferences=phone')
  const res = await doFetch('/login', { jar })
  assert.equal(res.status, 200)
  assert.ok(res.body.includes('window.electroMart'), 'JS sink present')
  // Raw reflection: the payload appears literally, NOT HTML-entity-escaped.
  assert.ok(res.body.includes('promoContext: "' + PAYLOAD + '"'), 'payload reflected raw inside the JS literal')
  assert.ok(!res.body.includes('promoContext: "&lt;script&gt;'), 'payload is NOT entity-escaped (that is the vuln)')
  // The numeric value is rendered as a plain integer (safe, separate channel).
  assert.match(res.body, /promoValue:\s*30\b/)
})

test('E: the Login sink allows a harmless JavaScript-string breakout (proof the sink is executable)', async () => {
  // Harmless breakout from `promoContext: "..."`: evaluates alert(1) while
  // collecting/transmitting nothing. This is the documented lab vulnerability.
  const breakout = '"+(alert(1))+"'
  const jar = new Jar()
  jar.absorb('promo_ctx=' + encodeURIComponent(breakout) + '; promo_ctx_val=30')
  const res = await doFetch('/login', { jar })
  assert.ok(res.body.includes('promoContext: "' + breakout + '",'),
    'payload is inserted raw inside the JS string (no escaping/entity encoding)')
  assert.ok(!res.body.includes('&quot;+(alert(1))'), 'quotes were not entity-escaped')
})

test('E: the designated Home sink reflects the crafted promo_ctx (no contextual escaping)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  authJar.absorb('promo_ctx=' + encodeURIComponent(PAYLOAD) + '; promo_ctx_val=30; shop_preferences=phone')
  const res = await doFetch('/home', { jar: authJar })
  const em = extractElectroMart(res.body)
  assert.equal(em.promoContext, PAYLOAD, 'home sink reflects the raw payload')
  assert.equal(em.promoValue, 30, 'home promo_value stays the numeric 30')
})

// ============================================================
//  TEST F — Regression testing (Requirement: no collateral damage)
// ============================================================

test('F: welcome still serves unauthenticated visitors; login + registration still work', async () => {
  const jar = new Jar()
  const w = await doFetch('/', { jar })
  assert.equal(w.status, 200)
  assert.ok(w.body.includes('ElectroMart'), 'welcome renders')
  assert.ok(!w.body.includes('duck{'), 'no flag leak on welcome')

  const { jar: ljar, res: lres } = await loginAs(VICTIM_USER, VICTIM_PASS)
  assert.equal(lres.status, 302, 'victim login still succeeds')
  // Registration (throwaway user) still works end to end.
  const rjar = new Jar()
  const uniq = 'test_' + Math.random().toString(36).slice(2, 10)
  const regPage = await doFetch('/register', { jar: rjar })
  const csrf = readCsrf(regPage.body)
  const regRes = await doFetch('/register', {
    jar: rjar, method: 'POST', redirect: 'manual',
    body: new URLSearchParams({
      username: uniq, email: uniq + '@example.com',
      first_name: 'T', last_name: 'U',
      password: 'Sup3rS3cret!x', confirm_password: 'Sup3rS3cret!x', csrf_token: csrf,
    }),
  })
  assert.equal(regRes.status, 302, 'registration still succeeds')
  void ljar
})

test('F: authenticated navbar remains correct', async () => {
  const { jar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const res = await doFetch('/home', { jar })
  assert.ok(/class="brand\b|brand-mark/.test(res.body), 'brand/nav present')
  assert.ok(res.body.includes('Store') && res.body.includes('Cart') && res.body.includes('Profile'),
    'navbar links present')
  assert.ok(res.body.includes('Log out'), 'logout control present')
  assert.ok(/avatar/.test(res.body), 'avatar present')
})

test('F: search + category + price filters work, and preference never overrides an active filter', async () => {
  const { jar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const search = await doFetch('/home?q=iphone', { jar })
  const searched = slugsFromHome(search.body)
  assert.ok(searched.length > 0 && searched.length < 20, 'search narrows results')
  const byCategory = await doFetch('/home?category=blender', { jar, headers: { Cookie: 'shop_preferences=phone' } })
  // Only blenders, no phone reordering injected by the preference cookie.
  const blenders = await doFetch('/home?category=blender', { jar })
  assert.deepEqual(slugsFromHome(byCategory.body), slugsFromHome(blenders.body),
    'active category filter wins; preference adds no phone reordering')
  const sorted = await doFetch('/home?sort=price-asc', { jar, headers: { Cookie: 'shop_preferences=tv' } })
  const prices = [...sorted.body.matchAll(/product-card__price">([\d,]+) EGP/g)].map((m) => Number(m[1].replace(/,/g, '')))
  for (let i = 1; i < prices.length; i++) assert.ok(prices[i - 1] <= prices[i], 'price-asc still ascending')
})

test('F: an active search overrides preference ordering (normal browser jar)', async () => {
  const jar = new Jar()
  await doFetch('/', { jar })
  const { jar: authJar } = await loginAs(VICTIM_USER, VICTIM_PASS)

  await doFetch('/home?preferences=phone', { jar: authJar })
  assert.equal(authJar.get('shop_preferences'), 'phone')
  const withPreference = slugsFromHome((await doFetch('/home?q=samsung', { jar: authJar })).body)

  await doFetch('/home?preferences=none', { jar: authJar })
  assert.equal(authJar.get('shop_preferences'), 'none')
  const withoutPreference = slugsFromHome((await doFetch('/home?q=samsung', { jar: authJar })).body)

  assert.ok(withPreference.length > 1, 'search returns multiple Samsung products')
  assert.deepEqual(withPreference, withoutPreference,
    'active search wins; shop_preferences does not reorder search results')
})

test('F: victim account + seed data remain intact; flag only visible on victim /profile', async () => {
  const { jar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const profile = await doFetch('/profile', { jar })
  assert.equal(profile.status, 200)
  const addr = /name="address"[\s\S]*?>([\s\S]*?)<\/textarea>/.exec(profile.body)?.[1] ?? ''
  assert.equal(addr.trim(), 'duck{XSS_to_AccountTakeOver}', 'victim flag present in Delivery address')
  // Public pages must not leak it.
  for (const path of ['/', '/login', '/register']) {
    const page = await doFetch(path)
    assert.ok(!page.body.includes('duck{XSS_to_AccountTakeOver}'), `flag leaked on ${path}`)
  }
  // 20 seeded products still reachable.
  const home = await doFetch('/home', { jar })
  assert.equal(new Set(slugsFromHome(home.body)).size, 20, 'all 20 seeded products present')
})

test('F: promo_ctx_val remains numeric + validated (out-of-range invalid rejected; never JS)', async () => {
  const { jar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  // Invalid / out-of-range values fall back to a safe numeric (never HTML/JS).
  for (const bad of ['<script>', '200', '-5', 'abc', '5.5', '9', '101']) {
    const page = await doFetch('/home', { jar, headers: { Cookie: 'promo_ctx_val=' + bad } })
    const em = extractElectroMart(page.body)
    assert.ok(Number.isFinite(em.promoValue), `promo_ctx_val parsed for value ${bad}`)
    assert.ok(em.promoValue >= 0 && em.promoValue <= 100, `promo_ctx_val in [0,100] for ${bad}`)
    if (bad === '101' || bad === '200' || bad === '-5' || bad === 'abc' || bad === '<script>' || bad === '5.5') {
      assert.equal(em.promoValue, 30, `invalid/out-of-range ${bad} -> safe default 30`)
    }
  }
  // A valid value in range is honoured.
  assert.equal(extractElectroMart((await doFetch('/home', { jar, headers: { Cookie: 'promo_ctx_val=45' } })).body).promoValue, 45)
})

test('F: unrelated pages (reviews/comments, profile) gain NO new injection sink', async () => {
  const { jar } = await loginAs(VICTIM_USER, VICTIM_PASS)
  const home = await doFetch('/home', { jar })
  const slug = slugsFromHome(home.body)[0]
  const detail = await doFetch('/product/' + slug, { jar })
  const csrf = readCsrf(detail.body)
  const marker = 'nosink-' + Date.now()
  const res = await doFetch('/product/' + slug + '/reviews', {
    jar, method: 'POST', redirect: 'manual',
    body: new URLSearchParams({ rating: '4', comment: marker + '<img src=x onerror=alert(1)>', csrf_token: csrf }),
  })
  assert.equal(res.status, 302)
  const after = await doFetch('/product/' + slug, { jar })
  assert.ok(after.body.includes(marker), 'review round-trips')
  // The review comment is HTML-ESCAPED (no new XSS sink in comments/reviews):
  // the injected tag must appear entity-escaped, never as a live tag.
  assert.ok(!after.body.includes('<img src=x onerror=alert(1)>'), 'review comment is NOT reflected raw (no new sink)')
  assert.ok(after.body.includes(marker) && /onerror=alert\(1\)/.test(after.body.replace('</', '</')),
    'comment rendered (escaped)')
  // A fresh registration must not expose a promo raw-JS sink either.
  const rjar = new Jar()
  const reg = await doFetch('/register', { jar: rjar })
  assert.ok(!/window\.electroMart/.test(reg.body), 'register page carries no promo raw-JS sink')
})

test('F: the only inline raw-JS promo sinks remain the two designated sites (home + login)', async () => {
  const fs = require('node:fs')
  const path = require('node:path')
  const viewsDir = path.join(__dirname, '..', 'views')
  const files = fs.readdirSync(viewsDir).filter((f) => f.endsWith('.ejs'))
  let sinkCount = 0
  for (const f of files) {
    const text = fs.readFileSync(path.join(viewsDir, f), 'utf8')
    const sinks = (text.match(/promoContext:\s*"\<%-/g) || []).length
    sinkCount += sinks
    if (f !== 'home.ejs' && f !== 'login.ejs') {
      assert.equal(sinks, 0, `${f} must not contain a promo raw-JS sink`)
    }
  }
  assert.equal(sinkCount, 2, 'exactly two designated raw-JS sinks exist (home + login)')
})
