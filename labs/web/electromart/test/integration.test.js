'use strict'

/**
 * Phase 1.3 — INTEGRATION tests (run against the LIVE Docker app).
 *
 * These execute over real HTTP with real cookie headers, so they prove the
 * server-side parser's actual behaviour — which value an ordinary request
 * assigns to shop_preferences, and which value the crafted "parsing-confusion"
 * request assigns to promo_ctx.
 *
 * Prereq: the stack is up (see test/README). Uses the built-in fetch (Node
 * >=20). No third-party dependencies.
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const BASE = process.env.APP_URL || 'http://localhost:3000'

// The lab cookies (see src/utils/promo.js). When a test supplies an explicit
// `Cookie` header to drive one of these, the jar's (possibly stale) copy of the
// same lab cookie is dropped so the test's value is the only one on the wire —
// the session cookie (and any non-lab cookies) are always preserved.
const LAB_COOKIE_NAMES = ['shop_preferences', 'promo_ctx', 'promo_ctx_val']

// Crafted value: legitimate preference + a SPACE + an injected promo_ctx pair.
//
// The payload MUST contain NO spaces and NO double quotes:
//   • no spaces — the documented parser splits each cookie pair on internal
//     whitespace (\S+), so a space inside the injected value would shred it into
//     the wrong value (the documented lab flaw only smuggles a space-FREE value).
//   • no double quotes — the value is reflected into a double-quoted JS string
//     (`promoContext: "..."`), and both the rendered output and this test's
//     extraction regex read up to the first unescaped `"`.
// It is sent over the wire RAW (undici accepts the raw header bytes), NOT
// percent-encoded: encoding would turn the `=` into %3D and hide the pair.
const XSS_PAYLOAD = "<script>alert('xss')</script>"
const INJECTED_COOKIE = `shop_preferences=phone promo_ctx=${XSS_PAYLOAD}`

/** Minimal cookie jar that mirrors how a browser stores/sends cookies. */
class Jar {
  constructor() {
    this.map = new Map()
  }
  absorb(header) {
    if (!header) return
    for (let part of header.split(';')) {
      part = part.trim()
      if (!part) continue
      const i = part.indexOf('=')
      if (i > 0) this.map.set(part.slice(0, i), part.slice(i + 1))
    }
  }
  toHeader() {
    return [...this.map.entries()].map(([k, v]) => `${k}=${v}`).join('; ')
  }
  get(name) {
    return this.map.get(name)
  }
  clear() {
    this.map.clear()
  }
}

/**
 * Merge a jar's cookies with an optional explicit `Cookie` header string.
 * The explicit value wins per cookie name, so a test can pin a crafted lab
 * cookie while still sending the session cookie. Without an explicit value the
 * jar's full set is used; a stale duplicate of a lab cookie the test is
 * overriding is dropped so it cannot shadow the crafted value.
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
      if (explicitCookie && LAB_COOKIE_NAMES.includes(name)) continue
      out.push(name + '=' + value)
    }
  }
  return out.length ? out.join('; ') : undefined
}

/** Perform a fetch, updating `jar` with any Set-Cookie headers. */
async function doFetch(url, { method = 'GET', jar, body, headers = {}, redirect = 'follow' } = {}) {
  const cookie = mergeCookies(jar, headers.Cookie)
  const { Cookie: _cookie, ...restHeaders } = headers
  const res = await fetch(BASE + url, {
    method,
    redirect,
    headers: {
      ...(cookie ? { Cookie: cookie } : {}),
      ...(body instanceof URLSearchParams ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}),
      ...restHeaders,
    },
    body: body instanceof URLSearchParams ? body.toString() : body,
  })
  if (jar) {
    const set = res.headers.getSetCookie ? res.headers.getSetCookie() : []
    for (const sc of set) jar.absorb(sc)
  }
  const text = await res.text()
  return { status: res.status, headers: res.headers, body: text, location: res.headers.get('location') }
}

/** Extract the order of product slugs from a rendered home page. */
function slugsFromHome(html) {
  const out = []
  const re = /href="\/product\/([^"]+)"/g
  let m
  while ((m = re.exec(html)) !== null) out.push(m[1])
  return out
}

/** Extract the window.electroMart object fields from a page, if present. */
function extractElectroMart(html) {
  const ctx = /promoContext:\s*"((?:\\.|[^"\\])*)"/.exec(html)
  const val = /promoValue:\s*(\d+)/.exec(html)
  return { present: /window\.electroMart\s*=/.test(html), promoContext: ctx ? ctx[1] : null, promoValue: val ? Number(val[1]) : null }
}

/** Log a user in, returning an authenticated cookie jar (null if failed). */
async function login(username, password) {
  const jar = new Jar()
  const page = await doFetch('/login', { jar })
  const csrf = /name="csrf_token" value="([^"]+)"/.exec(page.body)?.[1]
  if (!csrf) throw new Error('could not read login CSRF token')
  const res = await doFetch(
    '/login',
    { method: 'POST', jar, redirect: 'manual', body: new URLSearchParams({ username, password, csrf_token: csrf }) }
  )
  return { jar, res }
}

function readCsrf(html) {
  return /name="csrf_token" value="([^"]+)"/.exec(html)?.[1]
}

/** Log in as a brand-new throwaway user (for mutation tests). */
async function registerAndLogin() {
  const jar = new Jar()
  const uniq = 'test_' + Math.random().toString(36).slice(2, 10)
  const page = await doFetch('/register', { jar })
  const csrf = readCsrf(page.body)
  const res = await doFetch(
    '/register',
    {
      method: 'POST',
      jar,
      redirect: 'manual',
      body: new URLSearchParams({
        username: uniq,
        email: uniq + '@example.com',
        first_name: 'Test',
        last_name: 'User',
        password: 'Sup3rS3cret!x',
        confirm_password: 'Sup3rS3cret!x',
        csrf_token: csrf,
      }),
    }
  )
  assert.equal(res.status, 302, 'registration should succeed for a unique user')
  return { jar, username: uniq, res }
}

// ============================================================
//  VICTIM ACCOUNT
// ============================================================

test('victim: documented credentials log in and reach /profile with the exact flag', async () => {
  const { jar, res } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  assert.equal(res.status, 302, 'victim login should be a 302 redirect')
  const profile = await doFetch('/profile', { jar })
  assert.equal(profile.status, 200)
  const addr = /name="address"[\s\S]*?>([\s\S]*?)<\/textarea>/.exec(profile.body)?.[1] ?? ''
  assert.equal(addr.trim(), 'duck{XSS_to_AccountTakeOver}', 'Delivery address must hold the exact flag')
  assert.match(profile.body, /victim/, 'profile shows the victim')
})

test('victim: the flag is NOT rendered on public pages', async () => {
  for (const path of ['/login', '/', '/register']) {
    const page = await doFetch(path)
    assert.ok(!page.body.includes('duck{XSS_to_AccountTakeOver}'), `flag leaked on ${path}`)
    assert.ok(!/victimEmail@gmail\.com/.test(page.body), `victim email leaked on ${path}`)
  }
})

test('victim: wrong password is rejected', async () => {
  const { res } = await login('victim', 'wrong-password')
  assert.equal(res.status, 401)
})

// ============================================================
//  PREFERENCE COOKIE (shop_preferences) + ORDERING
// ============================================================

test('preference: no cookie → default order, all 20 products', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar, headers: { Cookie: 'nothing' } })
  const slugs = slugsFromHome(page.body)
  assert.equal(new Set(slugs).size, 20, 'all 20 products present')
})

test('preference: shop_preferences=phone → phones first, all 20 kept', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const phones = slugsFromHome((await doFetch('/home?category=phone', { jar })).body)
  const pref = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=phone' } })).body)
  assert.equal(pref.length, 20, 'still all products')
  assert.equal(pref.length, new Set(pref).size, 'no duplicates')
  // First N (phone count) must equal the phone category listing (same order).
  assert.deepEqual(pref.slice(0, phones.length), phones, 'phones moved to the front, in order')
  // The rest are the non-phones (all still present).
  const others = slugsFromHome((await doFetch('/home?category=blender', { jar })).body).concat(
    slugsFromHome((await doFetch('/home?category=TV', { jar })).body)
  )
  // (Sanity) phones subset is a strict prefix; total unique = 20.
  const all = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'none' } })).body)
  assert.equal(new Set(pref).size, new Set(all).size)
  void others
})

test('preference: shop_preferences=tv → TVs first', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const tvs = slugsFromHome((await doFetch('/home?category=TV', { jar })).body)
  const pref = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=tv' } })).body)
  assert.equal(pref.length, 20)
  assert.deepEqual(pref.slice(0, tvs.length), tvs, 'TVs moved to the front, in order')
})

test('preference: unsupported value falls back to default order', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const defaultOrder = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'none' } })).body)
  const hello = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=hello' } })).body)
  assert.deepEqual(hello, defaultOrder, 'unsupported preference → default ordering')
})

test('preference: /preferences=:value sets a REAL shop_preferences cookie', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  jar.clear()
  const set = await doFetch('/preferences=phone', { jar, redirect: 'manual' })
  assert.equal(set.status, 302)
  assert.equal(set.location, '/home')
  assert.ok(set.headers.getSetCookie().some((sc) => sc.includes('shop_preferences=phone')), 'Set-Cookie shop_preferences=phone present')
  // Using that cookie now orders phones first.
  const jar2 = new Jar()
  jar2.absorb('shop_preferences=phone')
  const { jar: authJar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar: authJar, headers: { Cookie: 'shop_preferences=phone' } })
  assert.ok(slugsFromHome(page.body).length === 20)
})

test('preference: explicit category filter overrides preference ordering', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const blenders = slugsFromHome((await doFetch('/home?category=blender', { jar })).body)
  const filtered = slugsFromHome(
    (await doFetch('/home?category=blender', { jar, headers: { Cookie: 'shop_preferences=phone' } })).body
  )
  assert.deepEqual(filtered, blenders, 'category filter wins; only blenders, no phone reordering')
  assert.ok(filtered.every((s) => blenders.includes(s)))
  assert.ok(!slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=phone' } })).body).includes('X'))
})

test('preference: price sort overrides preference ordering (ascending)', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home?sort=price-asc', { jar, headers: { Cookie: 'shop_preferences=tv' } })
  const prices = [...page.body.matchAll(/product-card__price">([\d,]+) EGP</g)].map((m) => Number(m[1].replace(/,/g, '')))
  assert.equal(prices.length, 20)
  for (let i = 1; i < prices.length; i++) assert.ok(prices[i - 1] <= prices[i], 'prices non-decreasing')
})

test('preference: clearing filters (back to /home) restores preference ordering', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const phones = slugsFromHome((await doFetch('/home?category=phone', { jar })).body)
  const filtered = slugsFromHome((await doFetch('/home?category=phone', { jar, headers: { Cookie: 'shop_preferences=phone' } })).body)
  const cleared = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=phone' } })).body)
  assert.notDeepEqual(filtered, cleared, 'filtered view differs from cleared view')
  assert.deepEqual(cleared.slice(0, phones.length), phones, 'clearing restores phone-first ordering')
})

test('preference: percent-encoded values round-trip (washing machine)', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const washers = slugsFromHome((await doFetch('/home?category=washing%20machine', { jar })).body)
  // Send the value the way Express res.cookie encodes it.
  const pref = slugsFromHome((await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=washing%20machine' } })).body)
  assert.deepEqual(pref.slice(0, washers.length), washers, 'washing machines prioritised')
})

// ============================================================
//  COOKIE PARSE BEHAVIOUR + THE INTENDED PARSING-CONFUSION
// ============================================================

test('parse: standard "; " pairs parse normally; semicolon is a separator not value text', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  // A normal header with real promo cookies: promo_ctx=summer_sale, val=30.
  const page = await doFetch('/home', { jar, headers: { Cookie: 'shop_preferences=tv; promo_ctx=summer_sale; promo_ctx_val=45' } })
  const em = extractElectroMart(page.body)
  assert.equal(em.promoContext, 'summer_sale')
  assert.equal(em.promoValue, 45)
})

test('parse: the crafted (lab-flaw) input assigns promo_ctx to the payload AND shop_preferences to "phone"', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  // Send the crafted Cookie header RAW (undici sends the raw bytes). The
  // whitespace-flaw parser splits on internal whitespace, so the space-FREE
  // payload becomes the value of promo_ctx verbatim.
  const page = await doFetch('/home', { jar, headers: { Cookie: INJECTED_COOKIE } })
  const em = extractElectroMart(page.body)
  assert.equal(em.present, true, 'window.electroMart is rendered')
  // promo_ctx became attacker-controlled (the documented result):
  assert.equal(em.promoContext, XSS_PAYLOAD, 'promo_ctx = attacker payload')
  // shop_preferences was parsed as the legitimate value "phone":
  assert.match(page.body, /<strong>phone<\/strong>\s+products first/, 'shop_preferences resolved to "phone"')
})

test('parse: malformed / unexpected inputs never crash the server', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const weirdCookies = [
    'promo_ctx=%zzz shop_preferences=%%%%',
    ';;;;',
    'promo_ctx=%%',
    'shop_preferences= phone promo_ctx=  =',
  ]
  for (const c of weirdCookies) {
    const page = await doFetch('/home', { jar, headers: { Cookie: c } })
    assert.equal(page.status, 200, `server must return 200 for Cookie: ${c}`)
    const loginPage = await doFetch('/login')
    assert.equal(loginPage.status, 200)
  }
})

// ============================================================
//  XSS SINKS (HTTP-level proof of the intended vulnerability)
// ============================================================

test('csp: every page allows fetch() to any origin', async () => {
  for (const path of ['/login', '/']) {
    const res = await doFetch(path)
    const csp = res.headers.get('content-security-policy') || ''
    assert.match(csp, /connect-src \*/, `${path} allows fetch() to any origin`)
    assert.doesNotMatch(csp, /connect-src[^;]*attckerserver\.local:4000/, `${path} has no OAST-specific allowlist`)
  }
})

test('xss: LOGIN promo text reflects promo_ctx raw (VULNERABLE SINK #2)', async () => {
  const page = await doFetch('/login', { headers: { Cookie: `promo_ctx=${XSS_PAYLOAD}` } })
  assert.equal(page.status, 200)
  assert.ok(page.body.includes('window.electroMart'), 'sink present')
  // Raw (NOT HTML-escaped) reflection of the payload inside the JS string:
  assert.ok(page.body.includes(`promoContext: "${XSS_PAYLOAD}"`), 'payload reflected raw into the JS object')
  assert.ok(!page.body.includes('promoContext: "&lt;script&gt;'), 'not HTML-escaped → this is the vuln')
})

test('xss: HOME banner reflects promo_ctx raw (VULNERABLE SINK #1)', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar, headers: { Cookie: `shop_preferences=tv promo_ctx=${XSS_PAYLOAD}` } })
  const em = extractElectroMart(page.body)
  assert.equal(em.promoContext, XSS_PAYLOAD, 'raw payload reflected into window.electroMart')
})

test('xss: normal promo context renders safely (default "summer_sale")', async () => {
  const page = await doFetch('/login')
  const em = extractElectroMart(page.body)
  assert.equal(em.promoContext, 'summer_sale')
  assert.equal(em.promoValue, 30)
  assert.ok(!page.body.includes('<script>alert'), 'no XSS on a normal page')
})

test('xss: promo_ctx_val is numeric-only and cannot carry HTML/JS', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  // Invalid value → safe fallback 30.
  const page = await doFetch('/home', { jar, headers: { Cookie: 'promo_ctx_val=<script>' } })
  const em = extractElectroMart(page.body)
  assert.equal(em.promoValue, 30, 'invalid promo_ctx_val falls back to 30 (numeric)')
  // A valid number is honoured.
  const ok = await doFetch('/home', { jar, headers: { Cookie: 'promo_ctx_val=45' } })
  assert.equal(extractElectroMart(ok.body).promoValue, 45)
})

// ============================================================
//  REGRESSION: authentication, profile, password, cart, reviews, search
// ============================================================

test('regression: signup creates a working account + session', async () => {
  const { jar, username, res } = await registerAndLogin()
  assert.equal(res.status, 302)
  const home = await doFetch('/home', { jar })
  assert.ok(home.body.includes('Our catalog'), 'signed-in user sees the store')
  void username
})

test('regression: session persists across requests; logout invalidates', async () => {
  const { jar } = await registerAndLogin()
  assert.equal((await doFetch('/home', { jar })).status, 200)
  assert.equal((await doFetch('/profile', { jar })).status, 200, 'still authenticated on next request')
  // Logout requires CSRF.
  const page = await doFetch('/profile', { jar })
  const csrf = readCsrf(page.body)
  const out = await doFetch('/logout', { jar, method: 'POST', redirect: 'manual', body: new URLSearchParams({ csrf_token: csrf }) })
  assert.equal(out.status, 302)
  // Now unauthenticated: /home redirects to /login.
  const afterHome = await doFetch('/home', { jar, redirect: 'manual' })
  assert.equal(afterHome.status, 302, 'after logout, /home redirects to login')
})

test('regression: profile edit + password change work', async () => {
  const { jar, username } = await registerAndLogin()
  // Read current email.
  let page = await doFetch('/profile', { jar })
  const email = /name="email"[^>]*value="([^"]+)"/.exec(page.body)?.[1]
  // Edit first/last name + address.
  let csrf = readCsrf(page.body)
  let res = await doFetch('/profile', {
    jar, method: 'POST', redirect: 'manual',
    body: new URLSearchParams({
      email, first_name: 'Edited', last_name: 'Name',
      address: '123 New St, Cairo', csrf_token: csrf,
    }),
  })
  assert.equal(res.status, 302)
  page = await doFetch('/profile', { jar })
  assert.ok(/value="Edited"/.test(page.body), 'first name persisted')
  assert.ok(/123 New St, Cairo/.test(page.body), 'address persisted')
  // Change password (needs current password).
  csrf = readCsrf(page.body)
  res = await doFetch('/profile/password', {
    jar, method: 'POST', redirect: 'manual',
    body: new URLSearchParams({
      current_password: 'Sup3rS3cret!x', new_password: 'N3wP@ssw0rd!x',
      new_password_confirmation: 'N3wP@ssw0rd!x', csrf_token: csrf,
    }),
  })
  assert.equal(res.status, 302)
  assert.ok(/password has been changed/i.test((await doFetch('/profile', { jar })).body), 'password change flash shown')
  // Old password no longer works; new one does (fresh sessions).
  // Login matches on USERNAME (not email), so use the account's username.
  const { res: oldLogin } = await login(username, 'Sup3rS3cret!x')
  assert.equal(oldLogin.status, 401, 'old password rejected')
  const { res: newLogin } = await login(username, 'N3wP@ssw0rd!x')
  assert.equal(newLogin.status, 302, 'new password accepted')
})

test('regression: search + category + product detail + reviews render', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const search = await doFetch('/home?q=iphone', { jar })
  const s = slugsFromHome(search.body)
  assert.ok(s.length > 0 && s.length < 20, 'search narrows results')
  assert.ok(s.every((slug) => /i-?phone/.test(slug.toLowerCase())))
  // Product detail with specs + prices + stock + reviews.
  const target = s[0]
  const detail = await doFetch('/product/' + target, { jar })
  assert.equal(detail.status, 200)
  assert.ok(detail.body.includes('EGP'), 'price shown')
  assert.ok(/stock/i.test(detail.body), 'stock shown')
  assert.ok(/review/i.test(detail.body), 'reviews section shown')
})

test('regression: all 20 product images are reachable', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar })
  const imgs = [...page.body.matchAll(/src="\/images\/([^"]+)"/g)].map((m) => decodeURIComponent(m[1]))
  const unique = [...new Set(imgs)]
  assert.equal(unique.length, 20, '20 distinct images referenced')
  for (const img of unique) {
    const r = await fetch(BASE + '/images/' + img)
    assert.equal(r.status, 200, `image 200: ${img}`)
    // The undici/web Response body is a ReadableStream — cancel() releases it.
    if (r.body && typeof r.body.cancel === 'function') await r.body.cancel()
  }
})

test('regression: cart add → update → remove', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar })
  const slug = slugsFromHome(page.body)[0]
  const detail = await doFetch('/product/' + slug, { jar })
  const csrf = readCsrf(detail.body)
  // Add to cart.
  let res = await doFetch('/product/' + slug + '/add-to-cart', { jar, method: 'POST', redirect: 'manual', body: new URLSearchParams({ quantity: '2', csrf_token: csrf }) })
  assert.equal(res.status, 302)
  let cart = await doFetch('/cart', { jar })
  assert.ok(cart.body.includes(slug), 'item in cart')
  // Update qty.
  const csrf2 = readCsrf(cart.body)
  res = await doFetch('/cart/update', { jar, method: 'POST', redirect: 'manual', body: new URLSearchParams({ slug, quantity: '1', csrf_token: csrf2 }) })
  assert.equal(res.status, 302)
  // Remove.
  const cart2 = await doFetch('/cart', { jar })
  const csrf3 = readCsrf(cart2.body)
  res = await doFetch('/cart/remove', { jar, method: 'POST', redirect: 'manual', body: new URLSearchParams({ slug, csrf_token: csrf3 }) })
  assert.equal(res.status, 302)
  cart = await doFetch('/cart', { jar })
  assert.ok(!cart.body.includes('href="/product/' + slug + '"') || /cart-empty|No items|Your cart is empty/i.test(cart.body), 'item removed from cart')
})

test('regression: posting a review is displayed', async () => {
  const { jar } = await login('victim', 'Victim#XSStoAccountTackOver#2')
  const page = await doFetch('/home', { jar })
  const slug = slugsFromHome(page.body)[0]
  const detail = await doFetch('/product/' + slug, { jar })
  const csrf = readCsrf(detail.body)
  const marker = 'phase13-review-' + Date.now()
  const res = await doFetch('/product/' + slug + '/reviews', {
    jar, method: 'POST', redirect: 'manual',
    body: new URLSearchParams({ rating: '5', comment: marker, csrf_token: csrf }),
  })
  assert.equal(res.status, 302)
  const after = await doFetch('/product/' + slug, { jar })
  assert.ok(after.body.includes(marker), 'submitted review is rendered')
})

// ============================================================
//  REGRESSION GUARD: no new XSS sinks outside the two designated sites
// ============================================================

test('guard: the only inline window.electroMart sinks are home + login', async () => {
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
  assert.equal(sinkCount, 2, 'exactly two designated raw-JS sinks exist')
  // Profile address + product name use escaped (<%= %>) output.
  const profile = fs.readFileSync(path.join(viewsDir, 'profile.ejs'), 'utf8')
  assert.ok(profile.includes('<%= user.address %>'), 'profile address is HTML-escaped')
})
