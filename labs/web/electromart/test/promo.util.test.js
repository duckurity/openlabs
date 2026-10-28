'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')
const promo = require('../src/utils/promo')

/**
 * The single crafted cookie the lab uses. The browser serialises it as ONE
 * cookie (`shop_preferences`) whose value contains a SPACE followed by the
 * injected `promo_ctx=<script>...</script>`. Under the CORRECT parser that
 * whole blob is just the value of shop_preferences (no XSS). Under the LAB
 * parser, splitting on whitespace exposes `promo_ctx=<script>...</script>` as
 * a separate pair, so promo_ctx becomes attacker-controlled.
 *
 * The trailing token has NO internal spaces, so it survives the whitespace split.
 */
const INJECTED = 'shop_preferences=phone promo_ctx=<script>alert("xss")</script>'

test('loadCookies — a normal, well-formed header is parsed correctly', () => {
  const r = promo.loadCookies('shop_preferences=phone')
  assert.equal(r.preferences, 'phone')
  assert.equal(r.promoCtx, 'summer_sale') // default
  assert.equal(r.promoVal, '30')          // default
})

test('loadCookies — standard "; " pairs are distinct; first wins, no overwrite', () => {
  const r = promo.loadCookies('promo_ctx=summer_sale; promo_ctx_val=30; shop_preferences=tv')
  assert.equal(r.preferences, 'tv')
  assert.equal(r.promoCtx, 'summer_sale')
  assert.equal(r.promoVal, '30')
  // A later duplicate name must NOT overwrite the first (no "merge/overwrite").
  const dup = promo.loadCookies('promo_ctx=legit; promo_ctx=attacker')
  assert.equal(dup.promoCtx, 'legit')
})

test('loadCookies — a semicolon is a pair separator, NOT a literal value part', () => {
  // "a value with a semicolon inside" is split into two pairs, proving the
  // standard behaviour: the semicolon is never treated as literal value text.
  const r = promo.loadCookies('promo_ctx=a;b')
  assert.ok(r.parsedPairs.includes('promo_ctx=a'))
  assert.ok(r.parsedPairs.includes('b'))
  assert.ok(!r.parsedPairs.includes('promo_ctx=a;b'), 'semicolon never survives as literal value text')
  assert.equal(r.promoCtx, 'a', 'the value is "a" (first-wins), NOT "a;b"')
})

test('loadCookies (LAB FLAW) — the injected value smuggles promo_ctx', () => {
  const r = promo.loadCookies(INJECTED)
  assert.equal(r.flawActive, true)
  assert.equal(r.preferences, 'phone', 'legitimate preference preserved')
  // The injected pair becomes attacker-controlled — the documented result.
  assert.equal(r.promoCtx, '<script>alert("xss")</script>')
})

test('loadCookies (CORRECT PARSER) — the same input does NOT smuggle promo_ctx', () => {
  // Simulate the remediation: disable the flaw and re-parse.
  const saved = promo.getLAB_COOKIE_FLAW_ENABLED()
  promo.setLAB_COOKIE_FLAW_ENABLED(false)
  try {
    const r = promo.loadCookies(INJECTED)
    assert.equal(r.flawActive, false)
    // Correct parser: the entire blob is the value of shop_preferences; promo_ctx
    // and promo_ctx_val keep their defaults → the injection is neutralised.
    assert.equal(r.preferences, 'phone promo_ctx=<script>alert("xss")</script>')
    assert.equal(r.promoCtx, 'summer_sale') // defaults — injection neutralised
    assert.equal(r.promoVal, '30')
  } finally {
    promo.setLAB_COOKIE_FLAW_ENABLED(saved)
  }
})

test('interpretPreferenceInput — ordinary values select a category and never touch promo_ctx', () => {
  for (const [raw, expected] of [
    ['phone', 'phone'],
    ['tv', 'TV'],
    ['washing machine', 'washing machine'],
    ['none', 'none'],
  ]) {
    const r = promo.interpretPreferenceInput(raw)
    assert.equal(r.category, expected, `category for ${raw}`)
    assert.equal(r.flawTriggered, false, `${raw} must not trigger the lab flaw`)
    assert.equal(r.injectedPromoCtx, null)
  }
  assert.equal(promo.interpretPreferenceInput('hello').category, null, 'unsupported value is rejected')
})

test('interpretPreferenceInput — the space-separated crafted value smuggles promo_ctx', () => {
  const r = promo.interpretPreferenceInput('phone promo_ctx=<script>alert(1)<script>')
  assert.equal(r.category, 'phone', 'leading preference is preserved')
  assert.equal(r.flawTriggered, true, 'flaw is reported as triggered')
  assert.equal(r.injectedPromoCtx, '<script>alert(1)<script>', 'embedded promo_ctx is surfaced')
  // The input is ONE query value: splitting it on '&' would find no promo_ctx.
  assert.equal(r.raw.includes('&'), false)
})

test('interpretPreferenceInput — embedded promo_ctx_val is ignored, never surfaced', () => {
  const r = promo.interpretPreferenceInput('phone promo_ctx=<script>alert(1)<script> promo_ctx_val=99')
  assert.equal(r.category, 'phone')
  assert.equal(r.injectedPromoCtx, '<script>alert(1)<script>')
  assert.equal(Object.hasOwn(r, 'promoVal'), false, 'no promo_ctx_val is derived from preference input')
})

test('interpretPreferenceInput — the correct (remediated) parser neutralises the injection', () => {
  const saved = promo.getLAB_COOKIE_FLAW_ENABLED()
  promo.setLAB_COOKIE_FLAW_ENABLED(false)
  try {
    const r = promo.interpretPreferenceInput('phone promo_ctx=<script>alert(1)<script>')
    assert.equal(r.flawTriggered, false)
    assert.equal(r.injectedPromoCtx, null)
    assert.equal(r.category, null, 'the whole blob is not a valid preference')
  } finally {
    promo.setLAB_COOKIE_FLAW_ENABLED(saved)
  }
})

test('resolvePromotion — normal defaults are exposed and safe', () => {
  const p = promo.resolvePromotion('shop_preferences=phone')
  assert.equal(p.preference, 'phone')
  assert.equal(p.promoContext, 'summer_sale')
  assert.equal(p.safeContext, 'summer_sale')
  assert.equal(p.promoValue, 30)
})

test('resolvePromotion — injected promo_ctx is exposed raw (the sink) but safeContext clamps', () => {
  const p = promo.resolvePromotion(INJECTED)
  assert.equal(p.promoContext, '<script>alert("xss")</script>') // raw → sink
  assert.equal(p.safeContext, 'summer_sale') // what a corrected app would show
  assert.equal(p.preference, 'phone')
})

test('safePromoValue — numeric 0–100, invalid falls back to 30, never HTML', () => {
  assert.equal(promo.safePromoValue('15'), 15)
  assert.equal(promo.safePromoValue('0'), 0)
  assert.equal(promo.safePromoValue('100'), 100)
  assert.equal(promo.safePromoValue('200'), 30)    // out of range → fallback
  assert.equal(promo.safePromoValue('-5'), 30)     // out of range
  assert.equal(promo.safePromoValue('abc'), 30)    // not numeric
  assert.equal(promo.safePromoValue('<script>'), 30) // never HTML/JS
  assert.equal(promo.safePromoValue('5.5'), 30)    // not an integer
})

test('loadCookies — percent-encoded values round-trip (e.g. "washing machine")', () => {
  // Express res.cookie percent-encodes values, so the wire format is:
  //   shop_preferences=washing%20machine
  // The parser must decode it back to the real category id for ordering.
  const r = promo.loadCookies('shop_preferences=washing%20machine')
  assert.equal(r.preferences, 'washing machine')
})

test('orderProductsByPreference — phone products first, nothing hidden', () => {
  const products = [
    { category: 'TV' }, { category: 'phone' }, { category: 'blender' },
    { category: 'phone' }, { category: 'stove' },
  ]
  const ordered = promo.orderProductsByPreference(products, 'phone')
  assert.equal(ordered[0].category, 'phone')
  assert.equal(ordered[1].category, 'phone')
  assert.equal(ordered.length, 5) // all preserved
  assert.ok(ordered.includes(products[2])) // originals intact
})

test('orderProductsByPreference — unsupported / none leaves order unchanged', () => {
  const products = [{ category: 'TV' }, { category: 'phone' }]
  assert.deepEqual(promo.orderProductsByPreference(products, 'none'), products)
  assert.deepEqual(promo.orderProductsByPreference(products, 'hello'), products)
})

test('jsStringEscape (REMEDIATION) — neutralises a script-breakout payload', () => {
  // The documented fix: escape for the JS-string context and neutralise `</`
  // so a crafted value can never close the <script> tag or break the literal.
  const evil = '"};console.log("pwned");var x = 1 < 2 ? 3 : </script><script>alert(1)'
  const safe = promo.jsStringEscape(evil)
  assert.ok(!safe.includes('</script>'), 'no raw closing script tag survives')
  assert.ok(!safe.includes('</'), 'no `</` sequence survives')
  // Round-trips to the SAME string when evaluated by a real JS engine — proves
  // the injected quotes never broke out of the string literal early.
  const roundTripped = eval('"' + safe + '"') // eslint-disable-line no-eval
  assert.equal(roundTripped, evil)
})
