'use strict'

const path = require('path')

/**
 * The documented lab victim seed (src/seed-victim.js). This is a deliberately
 * predictable, local-only lab account, not a real credential. The bot never
 * logs the password and never exposes it in page content.
 */
const LAB_DEFAULT_VICTIM = Object.freeze({
  username: 'victim',
  email: 'victimEmail@gmail.com',
  password: 'Victim#XSStoAccountTackOver#2',
})

const DEFAULTS = Object.freeze({
  baseUrl: 'http://app.test:3000',
  readyPath: '/api/health',
  // Internal OAST callback service. The hostname is a Compose network alias;
  // localhost inside the bot container would point at the bot itself.
  oastBaseUrl: 'http://attckerserver.local:4000',
  oastReadyPath: '/health',
  xssCheckEnabled: true,
  xssCheckTimeoutMs: 15_000,
  xssCheckNegativeWaitMs: 2_000,
  cycleIntervalMs: 60_000,
  timeoutMs: 30_000,
  maxRetries: 3,
  retryBaseDelayMs: 1_000,
  readyTimeoutMs: 120_000,
  readyPollMs: 2_000,
  shutdownTimeoutMs: 15_000,
  headless: true,
  screenshotsOnFailure: false,
  screenshotDir: path.join(process.cwd(), 'bot-artifacts', 'screenshots'),
  // Empty means discovery of every product card on /home. Set
  // BOT_PRODUCT_PATHS explicitly to restrict the cycle to a known subset.
  productPaths: [],
  commentLinksEnabled: true,
  maxCycles: 0,
  logLevel: 'info',
})

function parseBoolean(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback
  const normalised = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalised)) return true
  if (['0', 'false', 'no', 'off'].includes(normalised)) return false
  return fallback
}

function parseInteger(value, fallback, { min, max }, name, warnings) {
  if (value === undefined || value === null || value === '') return fallback
  const parsed = Number(value)
  if (!Number.isInteger(parsed)) {
    warnings.push(`${name} is not an integer; using default ${fallback}`)
    return fallback
  }
  if (parsed < min || parsed > max) {
    warnings.push(`${name} is outside [${min}, ${max}]; using default ${fallback}`)
    return fallback
  }
  return parsed
}

function parseBaseUrl(value, warnings, variableName = 'ELECTROMART_BASE_URL') {
  const raw = String(value || (variableName === 'OAST_BASE_URL' ? DEFAULTS.oastBaseUrl : DEFAULTS.baseUrl)).trim()
  let url
  try {
    url = new URL(raw)
  } catch (_error) {
    throw new Error(`${variableName} is not a valid URL`)
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error(`${variableName} must use http:// or https://`)
  }
  if (url.username || url.password) {
    throw new Error(`${variableName} must not contain credentials`)
  }
  if (url.search || url.hash) {
    throw new Error(`${variableName} must not contain a query string or fragment`)
  }
  const pathname = url.pathname.replace(/\/+$/, '')
  if (pathname && pathname !== '/') {
    warnings.push(`${variableName} has a path; it is treated as the base path`)
  }
  return `${url.origin}${pathname === '/' ? '' : pathname}`
}

function parseProductPaths(value, warnings) {
  // Empty/unset means catalog discovery, so the bot sees every product (and
  // every review section) the homepage currently exposes.
  if (value === undefined || value === null || String(value).trim() === '') {
    return []
  }
  const paths = String(value)
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean)

  if (paths.length === 0) {
    warnings.push('BOT_PRODUCT_PATHS produced an empty list; using catalog discovery')
    return []
  }

  const valid = []
  for (const item of paths) {
    if (!item.startsWith('/') || item.startsWith('//')) {
      warnings.push(`ignoring BOT_PRODUCT_PATHS entry "${item}" (must be a site-relative path)`)
      continue
    }
    valid.push(item)
  }
  if (valid.length === 0) {
    warnings.push('BOT_PRODUCT_PATHS contained no valid site-relative paths; using catalog discovery')
    return []
  }
  return valid
}

/**
 * Build the origin allowlist for links found in review comments. The configured
 * app origin is always allowed; extra origins must be explicit, http(s) URLs.
 * Paths are ignored because only origins are allowlisted.
 */
function parseAllowedLinkOrigins(value, baseUrl, warnings) {
  const origins = new Set([new URL(baseUrl).origin])
  if (value === undefined || value === null || String(value).trim() === '') {
    return [...origins]
  }

  for (const item of String(value).split(/[,\n]/).map((entry) => entry.trim()).filter(Boolean)) {
    let url
    try {
      url = new URL(item)
    } catch (_error) {
      warnings.push(`BOT_ALLOWED_LINK_ORIGINS entry "${item}" is not a valid URL; ignoring it`)
      continue
    }
    if (!['http:', 'https:'].includes(url.protocol)) {
      warnings.push(`BOT_ALLOWED_LINK_ORIGINS entry "${item}" must use http:// or https://; ignoring it`)
      continue
    }
    if (url.username || url.password) {
      warnings.push('BOT_ALLOWED_LINK_ORIGINS entries must not contain credentials; ignoring entry')
      continue
    }
    if (url.pathname !== '/' || url.search || url.hash) {
      warnings.push(`BOT_ALLOWED_LINK_ORIGINS entry "${item}" is reduced to its origin ${url.origin}`)
    }
    origins.add(url.origin)
  }
  return [...origins]
}

/**
 * Read, validate and normalise bot configuration from environment variables.
 * Permanent configuration problems throw before the loop starts, so they are
 * reported clearly instead of being retried forever as transient failures.
 *
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {{ config: object, warnings: string[] }}
 */
function loadConfig(env = process.env) {
  const warnings = []
  const baseUrl = parseBaseUrl(env.ELECTROMART_BASE_URL, warnings)
  const oastBaseUrl = parseBaseUrl(env.OAST_BASE_URL, warnings, 'OAST_BASE_URL')

  const username = String(env.VICTIM_USERNAME || LAB_DEFAULT_VICTIM.username).trim().toLowerCase()
  const email = String(env.VICTIM_EMAIL || LAB_DEFAULT_VICTIM.email).trim()
  // An empty VICTIM_PASSWORD intentionally falls back to the documented lab
  // default. Never trim a password: the configured value must be used verbatim.
  const password = env.VICTIM_PASSWORD ? String(env.VICTIM_PASSWORD) : LAB_DEFAULT_VICTIM.password

  if (!username) throw new Error('VICTIM_USERNAME must not be empty')
  if (!/^[a-z0-9_-]{3,30}$/.test(username)) {
    throw new Error('VICTIM_USERNAME must be 3–30 characters (letters, numbers, _, -)')
  }
  if (!email) throw new Error('VICTIM_EMAIL must not be empty')
  if (!password) throw new Error('VICTIM_PASSWORD must not be empty')

  const logLevel = String(env.BOT_LOG_LEVEL || DEFAULTS.logLevel).trim().toLowerCase()
  if (!['debug', 'info', 'warn', 'error'].includes(logLevel)) {
    warnings.push(`BOT_LOG_LEVEL "${logLevel}" is invalid; using "info"`)
  }

  let readyPath = String(env.BOT_READY_PATH || DEFAULTS.readyPath).trim() || DEFAULTS.readyPath
  if (!readyPath.startsWith('/')) {
    warnings.push('BOT_READY_PATH should start with "/"; a leading slash was added')
    readyPath = `/${readyPath}`
  }

  let oastReadyPath = String(env.BOT_OAST_READY_PATH || DEFAULTS.oastReadyPath).trim() || DEFAULTS.oastReadyPath
  if (!oastReadyPath.startsWith('/')) {
    warnings.push('BOT_OAST_READY_PATH should start with "/"; a leading slash was added')
    oastReadyPath = `/${oastReadyPath}`
  }

  const config = {
    baseUrl,
    readyPath,
    oastBaseUrl,
    oastReadyPath,
    xssCheckEnabled: parseBoolean(env.BOT_XSS_CHECK_ENABLED, DEFAULTS.xssCheckEnabled),
    xssCheckTimeoutMs: parseInteger(
      env.BOT_XSS_CHECK_TIMEOUT_MS,
      DEFAULTS.xssCheckTimeoutMs,
      { min: 2_000, max: 120_000 },
      'BOT_XSS_CHECK_TIMEOUT_MS',
      warnings
    ),
    xssCheckNegativeWaitMs: parseInteger(
      env.BOT_XSS_CHECK_NEGATIVE_WAIT_MS,
      DEFAULTS.xssCheckNegativeWaitMs,
      { min: 500, max: 10_000 },
      'BOT_XSS_CHECK_NEGATIVE_WAIT_MS',
      warnings
    ),
    cycleIntervalMs: parseInteger(
      env.BOT_CYCLE_INTERVAL_MS,
      DEFAULTS.cycleIntervalMs,
      { min: 1_000, max: 24 * 60 * 60 * 1_000 },
      'BOT_CYCLE_INTERVAL_MS',
      warnings
    ),
    timeoutMs: parseInteger(
      env.BOT_TIMEOUT_MS,
      DEFAULTS.timeoutMs,
      { min: 1_000, max: 10 * 60 * 1_000 },
      'BOT_TIMEOUT_MS',
      warnings
    ),
    maxRetries: parseInteger(
      env.BOT_MAX_RETRIES,
      DEFAULTS.maxRetries,
      { min: 0, max: 10 },
      'BOT_MAX_RETRIES',
      warnings
    ),
    retryBaseDelayMs: parseInteger(
      env.BOT_RETRY_BASE_DELAY_MS,
      DEFAULTS.retryBaseDelayMs,
      { min: 250, max: 60_000 },
      'BOT_RETRY_BASE_DELAY_MS',
      warnings
    ),
    readyTimeoutMs: parseInteger(
      env.BOT_READY_TIMEOUT_MS,
      DEFAULTS.readyTimeoutMs,
      { min: 5_000, max: 30 * 60 * 1_000 },
      'BOT_READY_TIMEOUT_MS',
      warnings
    ),
    readyPollMs: parseInteger(
      env.BOT_READY_POLL_MS,
      DEFAULTS.readyPollMs,
      { min: 250, max: 60_000 },
      'BOT_READY_POLL_MS',
      warnings
    ),
    shutdownTimeoutMs: parseInteger(
      env.BOT_SHUTDOWN_TIMEOUT_MS,
      DEFAULTS.shutdownTimeoutMs,
      { min: 1_000, max: 120_000 },
      'BOT_SHUTDOWN_TIMEOUT_MS',
      warnings
    ),
    headless: parseBoolean(env.BOT_HEADLESS, DEFAULTS.headless),
    screenshotsOnFailure: parseBoolean(
      env.BOT_SCREENSHOTS_ON_FAILURE,
      DEFAULTS.screenshotsOnFailure
    ),
    screenshotDir: path.resolve(env.BOT_SCREENSHOT_DIR || DEFAULTS.screenshotDir),
    productPaths: parseProductPaths(env.BOT_PRODUCT_PATHS, warnings),
    commentLinksEnabled: parseBoolean(
      env.BOT_COMMENT_LINKS_ENABLED,
      DEFAULTS.commentLinksEnabled
    ),
    allowedLinkOrigins: parseAllowedLinkOrigins(
      env.BOT_ALLOWED_LINK_ORIGINS,
      baseUrl,
      warnings
    ),
    // Test-only upper bound. 0 (default) means the bot runs indefinitely.
    maxCycles: parseInteger(
      env.BOT_MAX_CYCLES,
      DEFAULTS.maxCycles,
      { min: 0, max: 1_000_000 },
      'BOT_MAX_CYCLES',
      warnings
    ),
    logLevel: ['debug', 'info', 'warn', 'error'].includes(logLevel) ? logLevel : 'info',
    victim: { username, email, password },
  }

  if (config.maxCycles > 0) {
    warnings.push(`BOT_MAX_CYCLES=${config.maxCycles} is a test-only bound; the default is indefinite operation`)
  }
  if (!config.headless) {
    warnings.push('BOT_HEADLESS=false needs a display/Xvfb; headless mode is recommended in Docker')
  }

  return { config, warnings }
}

module.exports = {
  loadConfig,
  DEFAULTS,
  LAB_DEFAULT_VICTIM,
}
