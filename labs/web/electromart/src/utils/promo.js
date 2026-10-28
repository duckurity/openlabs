'use strict'

/**
 * ============================================================
 *  Promo / preference cookie handling (Phase 1.3 — XSS Lab)
 * ============================================================
 *
 * THREE cookies power the promotion banner and the homepage
 * ordering:
 *
 *   - `shop_preferences`  legitimate, NOT vulnerable. Value is one of
 *                         SUPPORTED (or 'none'). Controls homepage ordering.
 *   - `promo_ctx`         the promotion *name* shown in the banner /
 *                         login page.  ★ THIS IS THE VULNERABLE COOKIE:
 *                         it is reflected into inline JavaScript in the
 *                         templates, which is how the XSS executes.
 *   - `promo_ctx_val`     the discount percentage (numeric, 0–100).
 *                         Validated + coerced to an integer and rendered
 *                         ESCAPED.  It is deliberately kept separate from
 *                         the XSS sink so it is NOT a second injection point.
 *
 * ----------------------------------------------------------
 *  IMPORTANT COOKIE-PARSING BEHAVIOUR (documented lab flaw)
 * ----------------------------------------------------------
 *
 * Under normal browser rules a semicolon separates name/value pairs in the
 * Cookie request header, and browsers forbid storing a semicolon inside a
 * cookie value — so an attacker would NOT be able to smuggle a second cookie
 * through an ordinary `Set-Cookie`.  This lab reproduces the intended
 * "cookie injection / space-separated injected cookie" behaviour through a
 * clearly-scoped, lab-only parsing inconsistency (see loadCookies).
 *
 * DO NOT treat a semicolon as something that automatically merges or
 * overwrites cookies.  The behaviour below is deterministic and depends only
 * on this application's parser.
 */

/**
 * LAB-ONLY PARSE FLAG -------------------------------------------------
 * When this is true, loadCookies() runs in "legacy" mode and splits the
 * Cookie header on WHITESPACE instead of on '; '.  That turns a single
 * crafted value such as:
 *
 *   shop_preferences = phone promo_ctx <script>console.log('xss')</script>
 *
 * …into several key/value tokens, so a key the attacker never "owneds" —
 * `promo_ctx` — becomes attacker-controlled.
 *
 *   true  (default) → the intended vulnerable lab behaviour.
 *   false           → correct '; '-splitting. The injected cookie can no longer
 *                     be smuggled, which is also the documented remediation.
 *
 * This is a documented, scoped lab flaw. It does NOT replace the project's
 * cookie middleware and does NOT make any ordinary request misbehave.
 */
// Mutable so tests (and a future "remediation toggle") can switch the parser to
// its CORRECT '; '-splitting behaviour without editing this file.
let _labFlawEnabled = true
function getLabFlawEnabled() { return _labFlawEnabled }
function setLabFlawEnabled(value) { _labFlawEnabled = Boolean(value) }

/** Cookie names and defaults. */
const COOKIES = {
  PREFERENCES: { name: 'shop_preferences', defaultValue: 'none' },
  PROMO_CTX: { name: 'promo_ctx', defaultValue: 'summer_sale' },
  PROMO_VAL: { name: 'promo_ctx_val', defaultValue: '30' },
}

/** A value is "malformed" when it cannot be a legitimate shop_preferences. */
const VALID_PREFERENCE_RE = /^(none|phone|tv|washing machine|stove|blender|AC|water filter)$/

/** Lifetime for the lab cookies (30 days), matching the shop_preferences policy. */
const PROMO_COOKIE_MAXAGE = 30 * 24 * 60 * 60 * 1000

/**
 * Read the three lab cookies from a raw `Cookie` header string.
 *
 * @param {string} rawCookie  The raw value of the request `Cookie` header.
 * @param {boolean} [forceFlaw]  Optional. When provided, parse with exactly this
 *   parser regardless of the module-level flag: `true` runs the lab whitespace
 *   flaw, `false` runs the CORRECT `'; '`-splitting parser. Lets a caller compare
 *   both interpretations without mutating shared state.
 * @returns {{ preferences: string, promoCtx: string, promoVal: string,
 *             parsedPairs: string[], flawActive: boolean }}
 *   `parsedPairs` is an array of "name=value" strings showing EXACTLY what the
 *   parser saw — used by tests to prove which value each cookie was assigned.
 */
function loadCookies(rawCookie, forceFlaw) {
  rawCookie = rawCookie === undefined || rawCookie === null ? '' : String(rawCookie)
  const flawActive = forceFlaw === undefined ? _labFlawEnabled : Boolean(forceFlaw)
  // Standard: split on '; ' then trim each pair.  Lab flaw: also split every
  // pair on internal whitespace, producing extra name/token pairs.
  const parsedPairs = rawCookie
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((pair) => (flawActive ? (pair.match(/\S+/g) || []) : [pair]))
    .flat()
    .filter(Boolean)

  const result = {
    preferences: COOKIES.PREFERENCES.defaultValue,
    promoCtx: COOKIES.PROMO_CTX.defaultValue,
    promoVal: COOKIES.PROMO_VAL.defaultValue,
    parsedPairs,
    flawActive,
  }

  // First occurrence of a name wins (matches common first-wins cookie
  // behaviour). Duplicate names are therefore ignored, not overwritten —
  // a semicolon does NOT "merge or overwrite" later cookies.
  const seen = new Set()
  for (const pair of parsedPairs) {
    const eq = pair.indexOf('=')
    const name = eq === -1 ? pair : pair.slice(0, eq).trim()
    const value = eq === -1 ? '' : pair.slice(eq + 1).trim()
    if (!name || seen.has(name)) continue
    seen.add(name)
    // Values cross the wire percent-encoded (e.g. `washing machine` →
    // `washing%20machine`), so decode them defensively before using.
    const decodedName = decodeTokenSafe(name)
    const decodedValue = decodeTokenSafe(value)
    if (decodedName === COOKIES.PREFERENCES.name) result.preferences = decodedValue
    else if (decodedName === COOKIES.PROMO_CTX.name) result.promoCtx = decodedValue
    else if (decodedName === COOKIES.PROMO_VAL.name) result.promoVal = decodedValue
  }

  return result
}

/** Decode a percent-encoded header token; malformed sequences yield the raw text. */
function decodeTokenSafe(token) {
  try {
    return decodeURIComponent(token)
  } catch (_err) {
    return token
  }
}

/**
 * Return the SAFE, display-ready promotion context.
 *
 * Normal (trusted) values pass through unchanged, so ordinary promo cookies
 * behave exactly as before.  A value that is NOT a known context (i.e. the
 * lab-flaw-injected value) is clamped to the default so the banner never
 * breaks.  The *raw* value is deliberately still exposed separately to the
 * templates — that is the intended vulnerable rendering path.
 *
 * @param {string} promoCtx  Raw promo_ctx value from loadCookies.
 * @returns {string}  A safe promotion label.
 */
function safePromoContext(promoCtx) {
  return VALID_PREFERENCE_RE.test(String(promoCtx).trim()) ||
    KNOWN_PROMO_CONTEXTS.has(String(promoCtx).trim())
    ? String(promoCtx).trim()
    : COOKIES.PROMO_CTX.defaultValue
}

/** Promotions the store actually runs (used to decide "trusted" vs "injected"). */
const KNOWN_PROMO_CONTEXTS = new Set(['summer_sale', 'winter_sale', 'black_friday', 'no_promo'])

/**
 * Coerce promo_ctx_val into an integer percentage in [0, 100].
 * Invalid input falls back to the default (30).  It is NEVER treated as HTML.
 *
 * @param {string} promoVal  Raw promo_ctx_val value.
 * @returns {number}
 */
function safePromoValue(promoVal) {
  const n = String(promoVal).trim()
  const parsed = /^[0-9]+$/.test(n) ? parseInt(n, 10) : NaN
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) return Number(COOKIES.PROMO_VAL.defaultValue)
  return parsed
}

/** Human-readable promo title. */
function promoTitle(ctx) {
  const s = String(ctx).trim()
  if (!s) return 'Promotion'
  return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Build the values handed to the promotion banner / login templates.
 *
 *   - promoContext  → the RAW value (intended XSS sink; reflected via <%- %>)
 *   - safeContext   → the clamped label (what a corrected app would render)
 *   - promoTitle    → human-readable title from the SAFE context
 *   - promoValue    → numeric 0–100
 *   - preference    → the resolved shop_preferences value
 *   - flawActive    → whether the lab parse flaw is enabled
 */
function resolvePromotion(rawCookie) {
  const { preferences, promoCtx, promoVal } = loadCookies(rawCookie)
  const safeContext = safePromoContext(promoCtx)
  return {
    preference: preferences,
    promoContext: promoCtx,          // raw → reflected into JS (the vulnerability)
    safeContext,
    promoTitle: promoTitle(safeContext),
    promoValue: safePromoValue(promoVal),
    flawActive: _labFlawEnabled,
  }
}

/**
 * DECIDE whether the preference-update response should re-issue `promo_ctx`.
 *
 * This is the lab's intentional COOKIE-STATE TRANSITION that turns a
 * read-side parsing flaw into a stored-browser change.  It runs ONLY when the
 * documented parsing flaw is enabled AND the crafted input actually drives the
 * parser: the lab flaw parser (whitespace split) must disagree with the CORRECT
 * `'; '` parser about what `promo_ctx` is.  For any ordinary / well-formed
 * Cookie header the two parsers agree (defaults or a clean explicit value), so
 * the transition does NOT fire and the stored cookie is left untouched.
 *
 * The value written is the one the FLAWED parser produced (the attacker-
 * controlled one); `promo_ctx_val` is never part of this decision, so it can
 * never be driven from shop_preferences / the crafted preference input.
 *
 * @param {string} rawCookie  The raw request `Cookie` header.
 * @returns {{ trigger: boolean, value?: string, flawVal: string, correctVal: string }}
 *   `trigger` false → no re-sync (do not touch the cookie).
 *   `trigger` true and `value` non-empty → caller re-issues `promo_ctx=<value>`.
 */
function promoStateTransition(rawCookie) {
  const raw = rawCookie === undefined || rawCookie === null ? '' : String(rawCookie)
  if (!_labFlawEnabled) {
    return { trigger: false, flawVal: '', correctVal: '' }
  }
  const flawed = loadCookies(raw, true)   // the vulnerable whitespace parser
  const correct = loadCookies(raw, false) // the CORRECT '; ' parser (remediation)
  const changed = flawed.promoCtx !== correct.promoCtx
  if (!changed) {
    // Parse agreement means there is no injected value to persist — leaving the
    // stored cookie alone (no reset, no churn). This also covers the common
    // lab-state change where the browser already carries a crafted promo_ctx;
    // the two parsers agree that it IS the value, so we never clobber it.
    return { trigger: false, flawVal: flawed.promoCtx, correctVal: correct.promoCtx }
  }
  return { trigger: true, value: flawed.promoCtx, flawVal: flawed.promoCtx, correctVal: correct.promoCtx }
}

/**
 * Convenience for the preference-update routes: apply the lab state transition
 * to an Express response. Re-issues `Set-Cookie: promo_ctx=<value>` ONLY when
 * the documented flaw is enabled and the crafted input actually changed the
 * parsed `promo_ctx`. Returns the decision object (so a caller can log/inspect
 * it). Does NOT touch `promo_ctx_val` or `shop_preferences`.
 *
 * @param {import('express').Response} res
 * @param {string} rawCookie
 */
function applyPromoCtxTransition(res, rawCookie) {
  const decision = promoStateTransition(rawCookie)
  if (decision.trigger) {
    res.cookie(
      COOKIES.PROMO_CTX.name,
      decision.value,
      promoCookieOptions(COOKIES.PROMO_CTX.name)
    )
  }
  return decision
}

/**
 * Standard options for the lab promo/preference cookies (shared by every route
 * that issues them). `promo_ctx` / `shop_preferences` stay readable by the
 * legitimate client-side UI (httpOnly false); the session cookie stays
 * HttpOnly (see app.js). `path: '/'` scopes them to the whole ElectroMart origin
 * so the Login, Home, and preference pages can all read them.
 */
function promoCookieOptions(name) {
  // `name` is accepted for API symmetry; all three lab cookies share one policy.
  void name
  return {
    path: '/',
    sameSite: 'lax',
    maxAge: PROMO_COOKIE_MAXAGE,
    // lab-only: keep the promo/preference context readable to the page's JS;
    // a production store would make these HttpOnly and never reflect them.
    httpOnly: false,
  }
}

/**
 * The supported shop_preferences values (for the /preferences endpoint +
 * homepage ordering).  `none` means "no preference / default ordering".
 */
const SUPPORTED_PREFERENCES = ['phone', 'TV', 'washing machine', 'stove', 'blender', 'AC', 'water filter']

/**
 * Normalise a preference-selection value to one of the canonical category ids
 * (or `none`).  Returns `null` for anything the store does not support.
 *
 * Matching is case-insensitive so the existing lowercase URL form
 * (`preferences=phone`, `preferences=tv`) works alongside the canonical ids.
 */
function normalizePreference(value) {
  const raw = String(value === undefined || value === null ? '' : value).trim()
  if (!raw) return null
  if (raw.toLowerCase() === 'none') return 'none'
  return SUPPORTED_PREFERENCES.find((category) => category.toLowerCase() === raw.toLowerCase()) || null
}

/**
 * Interpret the `preferences` selection input (from `/home?preferences=...` or
 * the legacy `/preferences=:value` route).
 *
 * The LAB FLAW is the SAME whitespace-splitting mistake used by loadCookies():
 * the value is treated as a serialised cookie pair and, when the lab parser is
 * enabled, an embedded whitespace-separated `promo_ctx=...` token becomes a
 * second pair.  We prove it fired by comparing the flawed parse with the correct
 * `'; '` parse — exactly as promoStateTransition() does for Cookie headers.
 *
 * A normal value (`phone`, `tv`, `washing machine`, `none`) produces NO
 * promo_ctx change.  The crafted value
 *
 *     phone promo_ctx=<script>alert(1)<script>
 *
 * (a single query value, because a space does NOT delimit query parameters)
 * yields `category: 'phone'` plus the injected promo_ctx.
 *
 * IMPORTANT: only the promo_ctx name is ever surfaced from this input.
 * `promo_ctx_val` is deliberately ignored, so preference input can never
 * change the protected numeric discount.
 *
 * @param {string} rawInput
 * @returns {{
 *   raw: string,
 *   category: string|null,
 *   flawTriggered: boolean,
 *   injectedPromoCtx: string|null,
 *   parsedCategory: string
 * }}
 */
function interpretPreferenceInput(rawInput) {
  const raw = rawInput === undefined || rawInput === null ? '' : String(rawInput)
  // Frame the value exactly like a cookie pair so the documented flaw parser
  // (and its correct counterpart) is what decides whether promo_ctx was smuggled.
  const syntheticPair = `${COOKIES.PREFERENCES.name}=${raw}`
  const flawed = loadCookies(syntheticPair) // honours the lab-flaw toggle
  const correct = loadCookies(syntheticPair, false)
  const flawTriggered = getLabFlawEnabled() && flawed.promoCtx !== correct.promoCtx

  // When the flaw fires, the leading whitespace token is the preference and the
  // later token is the injected promo_ctx (first-wins, like a Cookie header).
  // Without the flaw the whole (possibly multi-word) value is the preference.
  const parsedCategory = flawTriggered ? flawed.preferences : correct.preferences

  return {
    raw,
    category: normalizePreference(parsedCategory),
    flawTriggered,
    injectedPromoCtx: flawTriggered ? flawed.promoCtx : null,
    parsedCategory,
  }
}

/**
 * Apply a preference selection to the response.
 *
 * Writes `shop_preferences` under the normal policy, and — ONLY when the
 * documented lab flaw fires — also writes the attacker-controlled `promo_ctx`.
 * `promo_ctx_val` is never written here or derived from the input.
 *
 * @param {import('express').Response} res
 * @param {string} rawInput
 * @returns {ReturnType<typeof interpretPreferenceInput> & { category: string }}
 */
function applyPreferenceInput(res, rawInput) {
  const interpreted = interpretPreferenceInput(rawInput)
  const category = interpreted.category || COOKIES.PREFERENCES.defaultValue
  res.cookie(COOKIES.PREFERENCES.name, category, promoCookieOptions(COOKIES.PREFERENCES.name))
  if (interpreted.flawTriggered) {
    res.cookie(
      COOKIES.PROMO_CTX.name,
      interpreted.injectedPromoCtx,
      promoCookieOptions(COOKIES.PROMO_CTX.name)
    )
  }
  return { ...interpreted, category }
}

/** Map a shop_preferences value to the category id the store uses for ordering. */
function preferenceCategory(preference) {
  const value = String(preference || 'none').trim().toLowerCase()
  // The store's category ids ('TV', 'AC') are lowercased for matching.
  if (value === 'tv' || value === 'ac') return value.toUpperCase()
  return value
}

/**
 * Order the homepage products so preferred-category items come first, then the
 * rest in the normal (name) order.  Nothing is hidden; explicit filters/sorts
 * are applied by the caller BEFORE this function and always take precedence.
 *
 * @param {Array<{category: string}>} products
 * @param {string} preference  A shop_preferences value.
 * @returns {Array}  New array; originals untouched.
 */
function orderProductsByPreference(products, preference) {
  const cat = preferenceCategory(preference)
  const isSupported = SUPPORTED_PREFERENCES.map((s) => preferenceCategory(s)).includes(cat)
  if (!isSupported || cat === 'none') return products

  const inCat = products.filter((p) => String(p.category).toLowerCase() === cat.toLowerCase())
  const rest = products.filter((p) => String(p.category).toLowerCase() !== cat.toLowerCase())
  return [...inCat, ...rest]
}

/**
 * ESCAPE a value for safe embedding INSIDE a JavaScript string literal that is
 * itself inside a <script> block.
 *
 * This is the DOCUMENTED REMEDIATION for the reflected XSS. It:
 *   1. Escapes backslashes and the quote that delimits the literal, so the
 *      value can never break out of the string.
 *   2. Escapes every `</` as `<\/`, so the value can never close the <script>
 *      tag and start a new one.
 *
 * Applying this to the sink means a crafted promo_ctx value is rendered as an
 * inert string and can no longer execute. (In a real app you would also remove
 * 'unsafe-inline' from the CSP; see README → Remediation.)
 *
 * @param {string} value
 * @returns {string}
 */
function jsStringEscape(value) {
  return String(value === undefined || value === null ? '' : value)
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
}

module.exports = {
  getLAB_COOKIE_FLAW_ENABLED: getLabFlawEnabled,
  setLAB_COOKIE_FLAW_ENABLED: setLabFlawEnabled,
  COOKIES,
  SUPPORTED_PREFERENCES,
  normalizePreference,
  interpretPreferenceInput,
  applyPreferenceInput,
  loadCookies,
  safePromoContext,
  safePromoValue,
  promoTitle,
  resolvePromotion,
  promoStateTransition,
  applyPromoCtxTransition,
  promoCookieOptions,
  preferenceCategory,
  orderProductsByPreference,
  jsStringEscape, // the documented remediation helper
  _internal: { KNOWN_PROMO_CONTEXTS, VALID_PREFERENCE_RE },
}
