'use strict'

const fs = require('fs/promises')
const path = require('path')

const { AuthenticationError, BotError, ShutdownError, WorkflowError } = require('./errors')
const { safeError } = require('./logger')
const { waitForApp, waitForOast } = require('./readiness')
const { createBrowserSession } = require('./browser-session')
const { retryOperation, classifyError } = require('./retry')
const { selectCommentLink, labPathLabel } = require('./comment-links')
const { shorten, throwIfAborted } = require('./util')

const LAB_COOKIE_NAMES = new Set(['shop_preferences', 'promo_ctx', 'promo_ctx_val'])
const VALID_PREFERENCES = new Set([
  'none',
  'phone',
  'tv',
  'washing machine',
  'stove',
  'blender',
  'ac',
  'water filter',
])
const PREFERENCE_LABELS = Object.freeze({
  phone: 'Phone',
  tv: 'TV',
  'washing machine': 'Washing Machine',
  stove: 'Stove',
  blender: 'Blender',
  ac: 'Air Conditioner',
  'water filter': 'Water Filter',
})

function appUrl(config, requestPath) {
  const suffix = String(requestPath).startsWith('/') ? String(requestPath) : `/${requestPath}`
  return `${config.baseUrl}${suffix}`
}

function currentPath(page) {
  try {
    return new URL(page.url()).pathname
  } catch (_error) {
    return ''
  }
}

function headerText(header) {
  return header.innerText().then((text) => text.replace(/\s+/g, ' ').trim())
}

async function assertPublicHeader(page, step) {
  const header = page.locator('header.site-header')
  await header.waitFor({ state: 'visible' })
  const text = await headerText(header)

  if ((await header.locator('form[action="/logout"]').count()) !== 0) {
    throw new WorkflowError({
      message: 'public page unexpectedly shows a logout control',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  if ((await header.locator('.auth-actions').count()) !== 0) {
    throw new WorkflowError({
      message: 'public page unexpectedly shows the authenticated header actions',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  if ((await header.locator('.avatar').count()) !== 0) {
    throw new WorkflowError({
      message: 'public page unexpectedly shows the profile avatar',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  for (const selector of ['a[href="/home"]', 'a[href="/cart"]', 'a[href="/profile"]']) {
    if ((await header.locator(selector).count()) !== 0) {
      throw new WorkflowError({
        message: `public page unexpectedly shows authenticated navigation (${selector})`,
        step,
        category: 'assertion',
        transient: false,
      })
    }
  }
  if ((await header.locator('a[href="/login"]').count()) === 0) {
    throw new WorkflowError({
      message: 'public page is missing the guest login link',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  if (!/log in/i.test(text)) {
    throw new WorkflowError({
      message: 'public header does not look like the guest header',
      step,
      category: 'assertion',
      transient: false,
    })
  }
}

async function assertAuthenticatedHeader(page, step) {
  const header = page.locator('header.site-header')
  await header.waitFor({ state: 'visible' })
  const text = await headerText(header)

  if ((await header.locator('form[action="/logout"] button').count()) === 0) {
    throw new AuthenticationError('authenticated header is missing the logout control')
  }
  if ((await header.locator('.avatar[href="/profile"]').count()) === 0) {
    throw new AuthenticationError('authenticated header is missing the profile icon')
  }
  if ((await header.locator('a[href="/profile"]').count()) === 0) {
    throw new AuthenticationError('authenticated header is missing the profile link')
  }
  if ((await header.locator('a[href="/login"]').count()) !== 0) {
    throw new AuthenticationError('authenticated header still shows a login link')
  }
  if ((await header.locator('a[href="/register"]').count()) !== 0) {
    throw new AuthenticationError('authenticated header still shows a register link')
  }
  if (/\b(Welcome|Login|Register)\b/i.test(text)) {
    throw new AuthenticationError('authenticated header still contains public navigation text')
  }
  void step
}

async function navigateOnce({
  page,
  config,
  cycleId,
  requestPath,
  readySelector,
  step,
  authenticated = false,
  expectedPath = null,
}) {
  const url = appUrl(config, requestPath)
  void cycleId

  const response = await page.goto(url, {
    waitUntil: 'domcontentloaded',
    timeout: config.timeoutMs,
  })

  if (!response) {
    throw new WorkflowError({
      message: `navigation returned no response for ${requestPath}`,
      step,
      category: 'navigation',
      transient: true,
    })
  }

  const status = response.status()
  const finalPath = currentPath(page)

  if (authenticated && finalPath === '/login') {
    throw new AuthenticationError(`protected page ${requestPath} redirected to the login page`)
  }
  if (expectedPath && finalPath !== expectedPath) {
    throw new WorkflowError({
      message: `expected ${expectedPath} but finished at ${finalPath || 'an unknown path'}`,
      step,
      category: 'assertion',
      transient: false,
    })
  }
  if (status >= 400) {
    throw new WorkflowError({
      message: `unexpected HTTP ${status} for ${requestPath}`,
      step,
      category: 'http',
      transient: status >= 500,
    })
  }

  if (readySelector) {
    await page.waitForSelector(readySelector, {
      state: 'visible',
      timeout: config.timeoutMs,
    })
  }

  return { status, finalPath }
}

function navigate(options) {
  const { config, logger, signal, cycleId, step } = options
  return retryOperation({
    config,
    logger,
    signal,
    cycleId,
    step,
    category: 'navigation',
    run: () => navigateOnce(options),
  })
}

async function runStep(ctx, name, run) {
  ctx.step = name
  if (ctx.crashed) throw ctx.crashed
  throwIfAborted(ctx.signal)

  ctx.logger.debug('step.begin', { cycleId: ctx.cycleId, step: name })
  try {
    const result = await run()
    if (ctx.crashed) throw ctx.crashed
    ctx.logger.info('step.ok', { cycleId: ctx.cycleId, step: name })
    return result
  } catch (error) {
    if (error instanceof ShutdownError) throw error
    const classified = classifyError(error, name)
    if (!classified.step) classified.step = name
    ctx.logger.warn('step.failed', {
      cycleId: ctx.cycleId,
      step: classified.step,
      category: classified.category,
      error: safeError(classified, ctx.logger.sanitize),
    })
    throw classified
  }
}

async function openWelcomePage(ctx) {
  const { page, config, cycleId, signal, step } = ctx
  await navigate({
    page,
    config,
    logger: ctx.logger,
    signal,
    cycleId,
    requestPath: '/',
    readySelector: 'header.site-header',
    step,
  })

  await assertPublicHeader(page, step)
  ctx.logger.info('welcome.loaded', { cycleId })
}

async function openLoginPage(ctx) {
  const { page, config, cycleId, signal, step } = ctx
  await navigate({
    page,
    config,
    logger: ctx.logger,
    signal,
    cycleId,
    requestPath: '/login',
    readySelector: 'form[action="/login"]',
    step,
  })

  const form = page.locator('form[action="/login"]')
  if ((await form.locator('#username').count()) === 0) {
    throw new WorkflowError({
      message: 'login page is missing the username field',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  if ((await form.locator('#password').count()) === 0) {
    throw new WorkflowError({
      message: 'login page is missing the password field',
      step,
      category: 'assertion',
      transient: false,
    })
  }
  await assertPublicHeader(page, step)
}

async function authenticateVictim(ctx) {
  const { page, config, cycleId, step } = ctx
  const form = page.locator('form[action="/login"]')

  await form.locator('#username').fill(config.victim.username)
  await form.locator('#password').fill(config.victim.password)

  try {
    // Playwright waits for the navigation initiated by the click. On rejected
    // credentials the page re-renders at /login with .general-error, so this
    // returns quickly instead of waiting the full navigation timeout.
    await form.locator('button[type="submit"]').click()
  } catch (error) {
    throw new WorkflowError({
      message: 'login form submission failed',
      step,
      category: 'auth',
      transient: true,
      cause: error,
    })
  }

  if (currentPath(page) !== '/home') {
    let visible = false
    try {
      const generalError = page.locator('.general-error')
      visible = (await generalError.count()) > 0 && (await generalError.first().isVisible())
    } catch (_error) {
      visible = false
    }

    if (!visible) {
      // Give a slow server a short, bounded chance to finish the redirect or
      // render the error without relying on a fixed long sleep.
      const outcome = await Promise.race([
        page
          .waitForURL((url) => url.pathname === '/home', { timeout: Math.min(config.timeoutMs, 5_000) })
          .then(() => 'home')
          .catch(() => 'home-timeout'),
        page
          .waitForSelector('.general-error', { state: 'visible', timeout: Math.min(config.timeoutMs, 5_000) })
          .then(() => 'error')
          .catch(() => 'error-timeout'),
      ])
      if (outcome === 'home') {
        visible = false
      } else if (outcome === 'error') {
        visible = true
      }
    }

    if (visible) {
      throw new AuthenticationError(
        'login was rejected by the application (invalid credentials or missing victim account)'
      )
    }
    if (currentPath(page) !== '/home') {
      throw new WorkflowError({
        message: 'login form submission did not reach the authenticated homepage',
        step,
        category: 'auth',
        transient: true,
      })
    }
  }

  await page.waitForSelector('header.site-header .auth-actions form[action="/logout"]', {
    state: 'visible',
    timeout: config.timeoutMs,
  })
  await assertAuthenticatedHeader(page, step)
  ctx.logger.info('login.succeeded', { cycleId, account: 'configured-victim' })
}

async function browseHomepage(ctx) {
  const { page, config, cycleId, signal, step } = ctx
  await navigate({
    page,
    config,
    logger: ctx.logger,
    signal,
    cycleId,
    requestPath: '/home',
    readySelector: '.catalog-section .product-card',
    step,
    authenticated: true,
  })

  const cards = page.locator('.catalog-section .product-card')
  const count = await cards.count()
  if (count < 1) {
    throw new WorkflowError({
      message: 'catalog contains no product cards',
      step,
      category: 'assertion',
      transient: true,
    })
  }
  const firstName = (await cards.first().locator('.product-card__name').innerText()).trim()
  if (!firstName) {
    throw new WorkflowError({
      message: 'first product card has no visible name',
      step,
      category: 'assertion',
      transient: true,
    })
  }

  ctx.logger.info('catalog.loaded', {
    cycleId,
    productCards: count,
    firstProduct: shorten(firstName, 80),
  })
  return { productCards: count, firstProduct: shorten(firstName, 80) }
}

async function returnToHomepage(ctx) {
  const { page, config, cycleId, signal, step } = ctx
  await navigate({
    page,
    config,
    logger: ctx.logger,
    signal,
    cycleId,
    requestPath: '/home',
    readySelector: '.catalog-section .product-card',
    step,
    authenticated: true,
  })

  await assertAuthenticatedHeader(page, step)
  ctx.logger.info('homepage.returned', { cycleId })
}

async function visitProduct(ctx, requestPath, step) {
  const { page, config, cycleId, signal } = ctx

  return retryOperation({
    config,
    logger: ctx.logger,
    signal,
    cycleId,
    step,
    category: 'product',
    run: async () => {
      await navigateOnce({
        page,
        config,
        cycleId,
        requestPath,
        readySelector: 'h1.product-detail__name',
        step,
        authenticated: true,
      })

      const name = (await page.locator('h1.product-detail__name').first().innerText()).trim()
      if (name.length < 2) {
        throw new WorkflowError({
          message: 'product detail has no visible product name',
          step,
          category: 'assertion',
          transient: true,
        })
      }

      const image = page.locator('img.product-detail__image').first()
      await image.waitFor({ state: 'visible', timeout: config.timeoutMs })
      const imageLoaded = await image.evaluate(async (element) => {
        try {
          if (!element.complete) await element.decode()
        } catch (_error) {
          return false
        }
        return Boolean(element.complete && element.naturalWidth > 0)
      })
      if (!imageLoaded) {
        throw new WorkflowError({
          message: 'product image did not load',
          step,
          category: 'assertion',
          transient: true,
        })
      }

      const specs = await page.locator('.specs-table__row').count()
      if (specs < 1) {
        throw new WorkflowError({
          message: 'product technical specifications are missing',
          step,
          category: 'assertion',
          transient: false,
        })
      }

      const reviews = page.locator('section.reviews-section').first()
      await reviews.waitFor({ state: 'visible', timeout: config.timeoutMs })
      const reviewsHeading = (await reviews.locator('h2').first().innerText()).trim()
      if (!/customer reviews/i.test(reviewsHeading)) {
        throw new WorkflowError({
          message: 'product review section is not available',
          step,
          category: 'assertion',
          transient: false,
        })
      }
      await page.locator('#review-form').first().waitFor({
        state: 'visible',
        timeout: config.timeoutMs,
      })

      // Only links inside rendered review comments are candidates. The app
      // safely linkifies comments; navigation links, the review form, and the
      // surrounding page chrome are deliberately excluded.
      const reviewLinkLocator = page.locator(
        'section.reviews-section .review-item__comment a.review-link'
      )
      const reviewLinkCount = await reviewLinkLocator.count()
      const commentLinks = []
      for (let index = 0; index < reviewLinkCount; index += 1) {
        const href = await reviewLinkLocator.nth(index).getAttribute('href')
        if (href) commentLinks.push(href)
      }

      ctx.logger.info('product.verified', {
        cycleId,
        path: requestPath,
        name: shorten(name, 80),
        specs,
        imageLoaded: true,
        reviews: true,
        reviewLinks: commentLinks.length,
      })
      return {
        path: requestPath,
        name: shorten(name, 80),
        specs,
        commentLinks,
      }
    },
  })
}

/**
 * Collect every product link from the current authenticated homepage. This is
 * the default mode: the bot should inspect each product's review section, not
 * just a fixed sample, because a player may post a review on any product.
 */
async function discoverProductPaths(ctx) {
  const { page, config, cycleId } = ctx
  const cards = page.locator('.catalog-section .product-card')
  const productCards = await cards.count()
  const baseOrigin = new URL(config.baseUrl).origin
  const paths = []
  const seen = new Set()

  for (let index = 0; index < productCards; index += 1) {
    const href = await cards.nth(index).getAttribute('href')
    if (!href) continue

    let resolved
    try {
      resolved = new URL(href, config.baseUrl)
    } catch (_error) {
      continue
    }
    if (resolved.origin !== baseOrigin) continue
    if (resolved.username || resolved.password || resolved.search || resolved.hash) continue

    const pathname = resolved.pathname.replace(/\/+$/, '')
    if (labPathLabel(pathname) !== '/product/:slug') continue
    if (seen.has(pathname)) continue
    seen.add(pathname)
    paths.push(pathname)
  }

  ctx.logger.info('products.discovered', {
    cycleId,
    productCards,
    productPaths: paths.length,
  })

  if (paths.length === 0) {
    throw new WorkflowError({
      message: 'catalog did not expose any product links',
      step: 'products',
      category: 'assertion',
      transient: true,
    })
  }
  return paths
}

async function browseConfiguredProducts(ctx) {
  const configuredPaths = ctx.config.productPaths
  const paths =
    configuredPaths.length > 0 ? configuredPaths : await discoverProductPaths(ctx)

  ctx.logger.info('products.selected', {
    cycleId: ctx.cycleId,
    source: configuredPaths.length > 0 ? 'explicit' : 'catalog',
    count: paths.length,
  })

  const visited = []
  const commentLinkCandidates = []
  for (let index = 0; index < paths.length; index += 1) {
    const requestPath = paths[index]
    const step = `product[${index + 1}]`
    const product = await visitProduct(ctx, requestPath, step)
    visited.push(product)
    for (const href of product.commentLinks) {
      commentLinkCandidates.push({ href, productPath: product.path })
    }
  }
  return { visited, commentLinkCandidates }
}

async function readLabCookies(ctx) {
  const cookies = await ctx.page.context().cookies(ctx.config.baseUrl)
  const result = {}
  for (const cookie of cookies) {
    if (LAB_COOKIE_NAMES.has(cookie.name)) result[cookie.name] = cookie.value
  }
  return result
}

function safePreferenceValue(value) {
  const raw = String(value === undefined || value === null ? '' : value).trim()
  if (!raw) return 'absent'
  return VALID_PREFERENCES.has(raw.toLowerCase()) ? raw : 'unexpected'
}

function observeCookieState(before, after) {
  const rawPromoValue = after.promo_ctx_val
  const promoValueNumeric =
    rawPromoValue === undefined ||
    (/^[0-9]+$/.test(String(rawPromoValue)) &&
      Number(rawPromoValue) >= 0 &&
      Number(rawPromoValue) <= 100)

  return {
    shopPreferences: safePreferenceValue(after.shop_preferences),
    shopPreferencesChanged: before.shop_preferences !== after.shop_preferences,
    promoContextChanged: before.promo_ctx !== after.promo_ctx,
    promoContextPresent: after.promo_ctx !== undefined,
    promoValueNumeric,
    promoValueSource: rawPromoValue === undefined ? 'default' : 'cookie',
    promoValueChanged: before.promo_ctx_val !== after.promo_ctx_val,
  }
}

/**
 * Describe the preference input without retaining its value. The query/path
 * value may contain a crafted marker, so only booleans leave this function.
 */
function describePreferenceInput(selected) {
  let value = null
  try {
    const url = new URL(selected.url)
    if (url.searchParams.has('preferences')) {
      value = url.searchParams.get('preferences')
    } else if (url.pathname.startsWith('/preferences=')) {
      value = decodeURIComponent(url.pathname.slice('/preferences='.length))
    }
  } catch (_error) {
    value = null
  }

  return {
    usesPreferenceInput: value !== null,
    craftedPreferenceInput:
      value !== null && /\s/.test(value) && /\bpromo_ctx\s*=/.test(value),
  }
}

async function recoverHomepage(ctx, step) {
  const { page, config, cycleId } = ctx
  try {
    await page.goto(appUrl(config, '/home'), {
      waitUntil: 'domcontentloaded',
      timeout: config.timeoutMs,
    })
    await page.waitForSelector('.catalog-section .product-card', {
      state: 'visible',
      timeout: config.timeoutMs,
    })
    await assertAuthenticatedHeader(page, step)
    return true
  } catch (error) {
    ctx.logger.warn('comment_link.recovery-failed', {
      cycleId,
      error: {
        name: error && error.name ? error.name : 'Error',
        message: 'could not return to the authenticated homepage',
      },
    })
    return false
  }
}

async function observeHomepageForCommentLink(ctx, cookies) {
  const { page, config } = ctx
  await page.waitForSelector('.catalog-section .product-card', {
    state: 'visible',
    timeout: config.timeoutMs,
  })

  const labels = (await page.locator('.catalog-section .product-card__category').allTextContents())
    .map((label) => label.trim())
    .filter(Boolean)
  if (labels.length === 0) {
    throw new WorkflowError({
      message: 'comment link reached the homepage but no product cards rendered',
      step: 'comment-link',
      category: 'assertion',
      transient: true,
    })
  }

  const preference = safePreferenceValue(cookies.shop_preferences)
  const expectedLabel = PREFERENCE_LABELS[String(preference).toLowerCase()] || null
  let preferenceOrderOk = null
  let preferenceHintMatches = null

  if (expectedLabel) {
    const expectedKey = expectedLabel.toLowerCase()
    const firstOther = labels.findIndex((label) => label.toLowerCase() !== expectedKey)
    preferenceOrderOk =
      labels[0].toLowerCase() === expectedKey &&
      (firstOther === -1 ||
        !labels.slice(firstOther).some((label) => label.toLowerCase() === expectedKey))

    const hint = page.locator('.pref-hint strong').first()
    if ((await hint.count()) === 0) {
      preferenceHintMatches = false
    } else {
      const hintText = (await hint.innerText()).trim()
      preferenceHintMatches = hintText.toLowerCase() === String(preference).toLowerCase()
    }
  }

  let bannerDiscountNumeric = null
  const discount = page.locator('.promo-banner__off').first()
  if ((await discount.count()) > 0) {
    const text = (await discount.innerText()).trim()
    const match = text.match(/(\d+)%/)
    bannerDiscountNumeric =
      Boolean(match) && Number(match[1]) >= 0 && Number(match[1]) <= 100
  }

  return {
    homepageObserved: true,
    productCards: labels.length,
    preference,
    preferenceOrderOk,
    preferenceHintMatches,
    bannerDiscountNumeric,
  }
}

async function followCommentLink(ctx, candidates) {
  const { page, config, cycleId, logger } = ctx

  const selection = selectCommentLink({
    candidates,
    baseUrl: config.baseUrl,
    allowedOrigins: config.allowedLinkOrigins,
    visitedUrls: new Set(),
  })

  for (const rejection of selection.rejected) {
    logger.info('comment_link.rejected', {
      cycleId,
      productPath: rejection.sourceProductPath,
      reason: rejection.reason,
      ...(rejection.origin ? { origin: rejection.origin } : {}),
    })
  }

  if (!selection.selected) {
    logger.info('comment_link.none', {
      cycleId,
      candidates: candidates.length,
      rejected: selection.rejected.length,
    })
    return { followed: false, reason: 'no-eligible-link' }
  }

  const selected = selection.selected
  const input = describePreferenceInput(selected)
  logger.info('comment_link.selected', {
    cycleId,
    productPath: selected.sourceProductPath,
    origin: selected.origin,
    path: selected.pathLabel,
    paramNames: selected.paramNames,
    usesPreferenceInput: input.usesPreferenceInput,
    craftedPreferenceInput: input.craftedPreferenceInput,
  })

  // Read-only snapshot; raw values never reach the logger.
  const before = await readLabCookies(ctx)

  let response
  try {
    response = await page.goto(selected.url, {
      waitUntil: 'domcontentloaded',
      timeout: config.timeoutMs,
    })
  } catch (error) {
    logger.warn('comment_link.navigation-failed', {
      cycleId,
      productPath: selected.sourceProductPath,
      path: selected.pathLabel,
      paramNames: selected.paramNames,
      error: {
        name: error && error.name ? error.name : 'Error',
        message: 'navigation failed or timed out',
      },
    })
    await recoverHomepage(ctx, 'comment-link.recover')
    return { followed: false, reason: 'navigation-failed' }
  }

  if (!response) {
    logger.warn('comment_link.navigation-failed', {
      cycleId,
      productPath: selected.sourceProductPath,
      path: selected.pathLabel,
      paramNames: selected.paramNames,
      error: { name: 'Error', message: 'navigation returned no response' },
    })
    await recoverHomepage(ctx, 'comment-link.recover')
    return { followed: false, reason: 'navigation-failed' }
  }

  const status = response.status()
  const finalPath = currentPath(page)
  if (status >= 400) {
    logger.warn('comment_link.navigation-failed', {
      cycleId,
      productPath: selected.sourceProductPath,
      path: selected.pathLabel,
      status,
      paramNames: selected.paramNames,
    })
    await recoverHomepage(ctx, 'comment-link.recover')
    return { followed: false, reason: 'http-error', status }
  }

  if (finalPath === '/login') {
    logger.warn('comment_link.session-lost', {
      cycleId,
      path: selected.pathLabel,
      finalPath: '/login',
    })
    return { followed: false, reason: 'redirected-to-login' }
  }

  await page.waitForSelector('header.site-header', {
    state: 'visible',
    timeout: config.timeoutMs,
  })
  await assertAuthenticatedHeader(page, 'comment-link')

  const after = await readLabCookies(ctx)
  const cookieObservation = observeCookieState(before, after)
  const destinationObservation =
    finalPath === '/home'
      ? await observeHomepageForCommentLink(ctx, after)
      : { homepageObserved: false }

  const observation = {
    cycleId,
    productPath: selected.sourceProductPath,
    origin: selected.origin,
    path: selected.pathLabel,
    finalPath: labPathLabel(finalPath) || 'other',
    status,
    paramNames: selected.paramNames,
    usesPreferenceInput: input.usesPreferenceInput,
    craftedPreferenceInput: input.craftedPreferenceInput,
    ...cookieObservation,
    ...destinationObservation,
  }
  logger.info('comment_link.observed', observation)

  const failures = []
  if (!cookieObservation.promoValueNumeric) failures.push('promo_ctx_val is not numeric')
  if (cookieObservation.shopPreferences === 'unexpected') {
    failures.push('shop_preferences is not a supported value')
  }
  if (destinationObservation.preferenceOrderOk === false) {
    failures.push('homepage ordering does not match shop_preferences')
  }
  if (destinationObservation.preferenceHintMatches === false) {
    failures.push('homepage preference hint does not match shop_preferences')
  }
  if (destinationObservation.bannerDiscountNumeric === false) {
    failures.push('promo banner discount is not numeric')
  }

  if (failures.length > 0) {
    throw new WorkflowError({
      message: failures.join('; '),
      step: 'comment-link',
      category: 'preference',
      transient: false,
    })
  }

  logger.info('comment_link.verified', {
    cycleId,
    productPath: selected.sourceProductPath,
    path: selected.pathLabel,
    finalPath: observation.finalPath,
    status,
    shopPreferences: cookieObservation.shopPreferences,
    shopPreferencesChanged: cookieObservation.shopPreferencesChanged,
    promoContextChanged: cookieObservation.promoContextChanged,
    promoValueNumeric: cookieObservation.promoValueNumeric,
    promoValueChanged: cookieObservation.promoValueChanged,
    craftedPreferenceInput: input.craftedPreferenceInput,
    homepageObserved: destinationObservation.homepageObserved,
    preferenceOrderOk: destinationObservation.preferenceOrderOk,
    preferenceHintMatches: destinationObservation.preferenceHintMatches,
    bannerDiscountNumeric: destinationObservation.bannerDiscountNumeric,
  })

  return {
    followed: true,
    reason: 'followed',
    path: selected.pathLabel,
    finalPath: observation.finalPath,
    status,
    usesPreferenceInput: input.usesPreferenceInput,
    craftedPreferenceInput: input.craftedPreferenceInput,
    ...cookieObservation,
    ...destinationObservation,
  }
}

async function followAllCommentLinks(ctx, candidates) {
  const { config, logger, cycleId } = ctx
  const results = []
  const seen = new Set()

  for (const candidate of candidates) {
    let key = candidate.href
    try {
      key = new URL(candidate.href, config.baseUrl).href
    } catch (_error) {
      key = candidate.href
    }
    if (seen.has(key)) continue
    seen.add(key)

    const index = results.length + 1
    const result = await runStep(ctx, `comment-link[${index}]`, () =>
      followCommentLink(ctx, [candidate])
    )
    results.push(result)

    // The requested cycle returns to Home immediately after each visited
    // comment link, then continues with the next link (if any).
    if (result.followed) {
      await runStep(ctx, `homepage-return[${index}]`, () => returnToHomepage(ctx))
    }
  }

  const followed = results.filter((result) => result.followed)
  if (followed.length > 0) {
    return {
      ...followed[0],
      followed: true,
      followedCount: followed.length,
      attempts: results.length,
    }
  }

  const first = results[0] || {}
  return {
    ...first,
    followed: false,
    followedCount: 0,
    attempts: results.length,
    reason: first.reason || 'no-eligible-link',
  }
}


async function logoutVictim(ctx) {
  const { page, config, cycleId, step } = ctx
  const logoutForm = page.locator('header.site-header form[action="/logout"]').first()
  await logoutForm.waitFor({ state: 'visible', timeout: config.timeoutMs })

  try {
    await Promise.all([
      page.waitForURL((url) => url.pathname === '/', { timeout: config.timeoutMs }),
      logoutForm.locator('button[type="submit"]').click(),
    ])
  } catch (error) {
    throw new WorkflowError({
      message: 'logout did not return to the public welcome page',
      step,
      category: 'auth',
      transient: true,
      cause: error,
    })
  }

  await assertPublicHeader(page, step)

  // Prove the session is no longer authenticated without leaving the welcome
  // page. The API request shares the browser context's cookies but does not
  // navigate the page, so the cycle can end on `/` as required.
  let verification
  try {
    verification = await page.request.get(appUrl(config, '/profile'), {
      maxRedirects: 0,
      timeout: config.timeoutMs,
    })
  } catch (error) {
    throw new WorkflowError({
      message: 'could not verify that logout invalidated the session',
      step: `${step}.verify`,
      category: 'auth',
      transient: true,
      cause: error,
    })
  }

  const status = verification.status()
  const location = verification.headers().location || ''
  let locationPath = ''
  try {
    locationPath = new URL(location, config.baseUrl).pathname
  } catch (_error) {
    locationPath = ''
  }

  if (status < 300 || status >= 400 || locationPath !== '/login') {
    throw new WorkflowError({
      message: 'logout did not invalidate the session; /profile still did not redirect to /login',
      step: `${step}.verify`,
      category: 'auth',
      transient: true,
    })
  }

  await assertPublicHeader(page, step)
  ctx.logger.info('logout.verified', {
    cycleId,
    sessionInvalidated: true,
    stayedOnWelcome: true,
  })
  return { sessionInvalidated: true, stayedOnWelcome: true }
}

/**
 * Replay the victim login immediately after logout in the SAME browser context.
 *
 * This is deliberately after logout: a review link may have written a crafted
 * `promo_ctx` cookie, and the Login page is the second reflection sink. Reusing
 * the context keeps that cookie alive so a login-page payload runs on the
 * replay. The replay is best-effort: a payload may cancel the form submit or
 * break the page, but the cycle still reports the outcome and closes cleanly.
 */
async function replayLoginAfterLogout(ctx) {
  const { page, config, cycleId, signal, step } = ctx
  let cookies = {}
  let outcome = 'failed'
  let finalPath = ''
  let succeeded = false

  try {
    await navigate({
      page,
      config,
      logger: ctx.logger,
      signal,
      cycleId,
      requestPath: '/login',
      readySelector: 'form[action="/login"]',
      step,
    })

    cookies = await readLabCookies(ctx)
    const form = page.locator('form[action="/login"]')
    await form.locator('#username').fill(config.victim.username)
    await form.locator('#password').fill(config.victim.password)

    try {
      await form.locator('button[type="submit"]').click()
    } catch (error) {
      ctx.logger.warn('login.replay.click-failed', {
        cycleId,
        error: {
          name: error && error.name ? error.name : 'Error',
          message: 'login replay click did not complete',
        },
      })
    }

    const waitMs = Math.min(config.timeoutMs, 5_000)
    outcome = await Promise.race([
      page
        .waitForURL((url) => url.pathname === '/home', { timeout: waitMs })
        .then(() => 'home')
        .catch(() => 'home-timeout'),
      page
        .waitForSelector('.general-error', { state: 'visible', timeout: waitMs })
        .then(() => 'error')
        .catch(() => 'error-timeout'),
    ])

    finalPath = currentPath(page)
    succeeded = outcome === 'home' && finalPath === '/home'
    if (succeeded) {
      try {
        await assertAuthenticatedHeader(page, step)
      } catch (_error) {
        succeeded = false
        outcome = 'stalled'
      }
    }
  } catch (error) {
    if (error instanceof ShutdownError) throw error
    finalPath = currentPath(page)
    ctx.logger.warn('login.replay.error', {
      cycleId,
      step,
      error: safeError(error, ctx.logger.sanitize),
    })
  }

  const result = {
    attempted: true,
    succeeded,
    outcome: succeeded
      ? 'succeeded'
      : outcome === 'error'
        ? 'rejected'
        : outcome === 'failed'
          ? 'failed'
          : 'prevented-or-stalled',
    finalPath: labPathLabel(finalPath) || 'other',
    promoContextPresent: cookies.promo_ctx !== undefined,
  }
  ctx.logger.info('login.replay', { cycleId, ...result })
  return result
}

async function captureFailure({ page, config, logger, cycleId, step }) {
  if (!config.screenshotsOnFailure || !page) return null

  try {
    await fs.mkdir(config.screenshotDir, { recursive: true })
    const safeCycle = String(cycleId)
      .replace(/[^a-z0-9_.-]+/gi, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 50)
    const safeStep = String(step || 'failure')
      .replace(/[^a-z0-9_.-]+/gi, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 50)
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `${stamp}-${safeCycle}-${safeStep}.png`
    const filePath = path.join(config.screenshotDir, filename)

    // Mask the flag/address and all password inputs so a diagnostic image
    // cannot leak a credential or the training flag.
    const masks = [
      page.locator('#address'),
      page.locator('textarea[name="address"]'),
      page.locator('#password'),
      page.locator('#current_password'),
      page.locator('#new_password'),
      page.locator('#new_password_confirmation'),
    ]

    await page.screenshot({
      path: filePath,
      fullPage: true,
      mask: masks,
      maskColor: '#ff00ff',
    })
    logger.warn('screenshot.saved', { cycleId, step, file: filename })
    return filePath
  } catch (error) {
    logger.warn('screenshot.failed', {
      cycleId,
      step,
      error: logger.sanitize(error && error.message ? error.message : error),
    })
    return null
  }
}

/**
 * Run exactly one complete victim workflow in a fresh browser/context. The
 * caller's persistent loop is responsible for waiting and starting the next
 * cycle only after this promise settles.
 */
async function runVictimCycle({
  config,
  logger,
  signal,
  cycleId,
  cycleNumber,
  onResources = () => {},
}) {
  const startedAt = Date.now()
  const ctx = {
    config,
    logger,
    signal,
    cycleId,
    cycleNumber,
    step: 'readiness',
    page: null,
    crashed: null,
  }

  let session = null

  try {
    await runStep(ctx, 'readiness', async () => {
      const app = await waitForApp({ config, logger, signal, cycleId })
      const oast = await waitForOast({ config, logger, signal, cycleId })
      return { app, oast }
    })

    session = await retryOperation({
      config,
      logger,
      signal,
      cycleId,
      step: 'browser.start',
      category: 'browser',
      run: () => createBrowserSession({ config, logger, cycleId, signal }),
    })
    onResources(session)
    throwIfAborted(signal)

    ctx.page = session.page
    session.page.on('crash', () => {
      ctx.crashed = new WorkflowError({
        message: 'page crashed',
        step: ctx.step,
        category: 'browser',
        transient: true,
      })
      logger.error('browser.page-crashed', { cycleId, step: ctx.step })
    })
    session.page.on('dialog', (dialog) => {
      // The normal browsing workflow never expects a dialog. Dismissing it
      // avoids a hung page without executing anything from page content.
      dialog.dismiss().catch(() => {})
    })

    await runStep(ctx, 'welcome', () => openWelcomePage(ctx))
    await runStep(ctx, 'login-page', () => openLoginPage(ctx))
    await runStep(ctx, 'authenticate', () => authenticateVictim(ctx))

    const homepage = await runStep(ctx, 'homepage', () => browseHomepage(ctx))
    const productBrowse = await runStep(ctx, 'products', () => browseConfiguredProducts(ctx))

    let commentLink = { followed: false, reason: 'disabled' }
    if (config.commentLinksEnabled) {
      if (productBrowse.commentLinkCandidates.length === 0) {
        logger.debug('comment_link.none', { cycleId, reason: 'no-candidates' })
        commentLink = { followed: false, reason: 'no-candidates' }
      } else {
        commentLink = await followAllCommentLinks(ctx, productBrowse.commentLinkCandidates)
      }
    } else {
      logger.debug('comment_link.disabled', { cycleId })
    }

    // Whether a review link was followed or not, always come back to the
    // authenticated homepage before logging out.
    await runStep(ctx, 'homepage-return', () => returnToHomepage(ctx))
    await runStep(ctx, 'logout', () => logoutVictim(ctx))

    // Replay the login in the same context so a crafted promo_ctx written by a
    // review link is still present when the Login page renders.
    const loginReplay = await runStep(ctx, 'login-replay', () => replayLoginAfterLogout(ctx))

    return {
      durationMs: Date.now() - startedAt,
      homepage,
      productsVisited: productBrowse.visited.length,
      products: productBrowse.visited.map((product) => product.path),
      returnedHome: true,
      loggedOut: true,
      loginReplay,
      commentLink,
    }
  } catch (error) {
    if (error instanceof ShutdownError || signal.aborted) {
      const shutdown = error instanceof ShutdownError ? error : new ShutdownError()
      if (!shutdown.step) shutdown.step = ctx.step
      logger.info('cycle.aborted', { cycleId, step: shutdown.step })
      throw shutdown
    }

    const classified =
      error instanceof BotError
        ? error
        : new WorkflowError({
            message: error && error.message ? error.message : String(error),
            step: ctx.step,
            category: 'workflow',
            transient: true,
            cause: error,
          })

    await captureFailure({
      page: ctx.page,
      config,
      logger,
      cycleId,
      step: classified.step || ctx.step,
    })

    throw classified
  } finally {
    ctx.page = null
    if (session) {
      await session.close()
      onResources(null)
    }
  }
}

module.exports = {
  runVictimCycle,
  appUrl,
  assertPublicHeader,
  assertAuthenticatedHeader,
}
