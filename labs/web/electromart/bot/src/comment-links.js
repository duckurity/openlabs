'use strict'

/**
 * Validate links discovered in review comments before the bot follows them.
 *
 * This module is intentionally independent of Playwright so the origin/path
 * policy can be unit-tested without a browser. The bot never treats comment
 * text as instructions: a candidate must resolve to an explicitly allowed
 * origin and a known GET page of the ElectroMart lab.
 */

// Only routes that are safe to open during the comment-link observation. In
// particular, /profile is intentionally excluded so a comment cannot send the
// bot to the page containing the Delivery Address.
const LAB_PATH_RULES = Object.freeze([
  { pattern: /^\/home$/, label: '/home' },
  { pattern: /^\/preferences=[^/]+$/, label: '/preferences=:value' },
  { pattern: /^\/product\/[^/]+$/, label: '/product/:slug' },
  { pattern: /^\/login$/, label: '/login' },
  { pattern: /^\/register$/, label: '/register' },
  { pattern: /^\/cart$/, label: '/cart' },
])

function normalizePathname(pathname) {
  if (pathname === '/') return '/'
  return String(pathname || '').replace(/\/+$/, '') || '/'
}

/** Return the safe log label for an allowed lab path, or null. */
function labPathLabel(pathname) {
  const normalized = normalizePathname(pathname)
  const rule = LAB_PATH_RULES.find((item) => item.pattern.test(normalized))
  return rule ? rule.label : null
}

/**
 * Validate one candidate href.
 *
 * @param {object} options
 * @param {string} options.href
 * @param {string} options.baseUrl
 * @param {string[]} options.allowedOrigins
 * @param {Set<string>} [options.visitedUrls]
 * @returns {{
 *   ok: boolean,
 *   reason?: string,
 *   origin?: string,
 *   pathname?: string,
 *   pathLabel?: string,
 *   paramNames?: string[],
 *   key?: string,
 *   url?: string
 * }}
 */
function validateCommentLink({
  href,
  baseUrl,
  allowedOrigins,
  visitedUrls = new Set(),
}) {
  const raw = String(href === undefined || href === null ? '' : href).trim()
  if (!raw) return { ok: false, reason: 'empty-href' }

  let resolved
  try {
    resolved = new URL(raw, baseUrl)
  } catch (_error) {
    return { ok: false, reason: 'malformed-url' }
  }

  if (!['http:', 'https:'].includes(resolved.protocol)) {
    return { ok: false, reason: 'unsupported-scheme', origin: resolved.origin }
  }
  if (resolved.username || resolved.password) {
    return { ok: false, reason: 'credentials-in-url', origin: resolved.origin }
  }

  const origins = new Set(allowedOrigins || [])
  if (!origins.has(resolved.origin)) {
    return { ok: false, reason: 'external-origin', origin: resolved.origin }
  }

  // Keep the destination inside the configured application base path. The
  // default lab base URL has no path, so this is normally a no-op.
  const base = new URL(baseUrl)
  const basePath = normalizePathname(base.pathname)
  const pathname = normalizePathname(resolved.pathname)
  if (basePath !== '/' && pathname !== basePath && !pathname.startsWith(`${basePath}/`)) {
    return { ok: false, reason: 'outside-base-path', origin: resolved.origin }
  }

  const pathLabel = labPathLabel(pathname)
  if (!pathLabel) {
    return { ok: false, reason: 'outside-lab-scope', origin: resolved.origin }
  }

  // The fragment never affects the server or the loop guard.
  resolved.hash = ''
  const key = `${resolved.origin}${resolved.pathname}${resolved.search}`
  if (visitedUrls.has(key)) {
    return { ok: false, reason: 'duplicate-link', origin: resolved.origin, pathname, pathLabel }
  }

  return {
    ok: true,
    origin: resolved.origin,
    pathname,
    pathLabel,
    paramNames: [...resolved.searchParams.keys()],
    key,
    url: resolved.toString(),
  }
}

/**
 * Pick the first eligible comment link and report safe rejection reasons for
 * the rest. Candidate hrefs and query values are never copied into the result
 * used for logging; only origins, reasons and path labels are returned.
 *
 * @param {object} options
 * @param {Array<{href: string, productPath?: string}>} options.candidates
 * @returns {{
 *   selected: (object & { sourceProductPath: string }) | null,
 *   rejected: Array<{ sourceProductPath: string, reason: string, origin?: string }>
 * }}
 */
function selectCommentLink({
  candidates,
  baseUrl,
  allowedOrigins,
  visitedUrls = new Set(),
}) {
  const rejected = []
  for (const candidate of candidates || []) {
    const validation = validateCommentLink({
      href: candidate.href,
      baseUrl,
      allowedOrigins,
      visitedUrls,
    })
    if (validation.ok) {
      return {
        selected: {
          ...validation,
          sourceProductPath: candidate.productPath || '',
        },
        rejected,
      }
    }
    rejected.push({
      sourceProductPath: candidate.productPath || '',
      reason: validation.reason || 'rejected',
      ...(validation.origin ? { origin: validation.origin } : {}),
    })
  }
  return { selected: null, rejected }
}

module.exports = {
  LAB_PATH_RULES,
  validateCommentLink,
  selectCommentLink,
  labPathLabel,
}
