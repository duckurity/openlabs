'use strict'

const fs = require('fs')
const path = require('path')

/**
 * OAST service configuration.
 *
 * The callback hostname is deliberately the lab-only name
 * `attckerserver.local`, which resolves through the Compose network alias.
 * `localhost` inside a container would point at the container itself, so the
 * generated callback URL always uses the configured Docker hostname.
 */

const DEFAULTS = Object.freeze({
  host: '0.0.0.0',
  port: 4000,
  publicHost: 'attckerserver.local',
  publicPort: 4000,
  publicScheme: 'http',
  maxInteractions: 1000,
  dashboardLimit: 100,
  maxBodyBytes: 16 * 1024,
  requestTimeoutMs: 10_000,
  shutdownTimeoutMs: 8_000,
  logLevel: 'info',
})

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

function parsePublicUrl(raw, warnings) {
  if (!raw) return null
  let url
  try {
    url = new URL(String(raw).trim())
  } catch (_error) {
    warnings.push('OAST_PUBLIC_URL is not a valid URL; using OAST_PUBLIC_HOST/OAST_PUBLIC_PORT instead')
    return null
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    warnings.push('OAST_PUBLIC_URL must use http:// or https://; using host/port settings instead')
    return null
  }
  if (url.username || url.password) {
    warnings.push('OAST_PUBLIC_URL must not contain credentials; using host/port settings instead')
    return null
  }
  if (url.pathname !== '/' || url.search || url.hash) {
    warnings.push('OAST_PUBLIC_URL must be an origin without a path, query, or fragment; using host/port settings instead')
    return null
  }
  return url.origin
}

function parseHostname(value, fallback, name, warnings) {
  const raw = String(value === undefined || value === null || value === '' ? fallback : value).trim()
  // A hostname only: no scheme, path, port, credentials, or whitespace.
  if (!/^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$/i.test(raw) || raw.includes('..')) {
    warnings.push(`${name} is not a valid hostname; using default ${fallback}`)
    return fallback
  }
  return raw
}

function readBuildId() {
  try {
    const value = fs.readFileSync(path.join(__dirname, '..', 'build-id'), 'utf8').trim()
    return value || 'dev'
  } catch (_error) {
    return 'dev'
  }
}

/**
 * Read and validate OAST configuration from environment variables.
 *
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {{ config: object, warnings: string[] }}
 */
function loadConfig(env = process.env) {
  const warnings = []

  const port = parseInteger(
    env.OAST_PORT || env.PORT,
    DEFAULTS.port,
    { min: 1, max: 65_535 },
    'OAST_PORT',
    warnings
  )
  const publicPort = parseInteger(
    env.OAST_PUBLIC_PORT,
    port,
    { min: 1, max: 65_535 },
    'OAST_PUBLIC_PORT',
    warnings
  )
  const publicHost = parseHostname(
    env.OAST_PUBLIC_HOST,
    DEFAULTS.publicHost,
    'OAST_PUBLIC_HOST',
    warnings
  )
  const explicitPublicUrl = parsePublicUrl(env.OAST_PUBLIC_URL, warnings)
  const publicUrl = explicitPublicUrl || `http://${publicHost}:${publicPort}`

  const logLevelRaw = String(env.OAST_LOG_LEVEL || DEFAULTS.logLevel).trim().toLowerCase()
  const logLevel = ['debug', 'info', 'warn', 'error'].includes(logLevelRaw)
    ? logLevelRaw
    : 'info'
  if (logLevel !== logLevelRaw) {
    warnings.push(`OAST_LOG_LEVEL "${logLevelRaw}" is invalid; using "info"`)
  }

  const maxInteractions = parseInteger(
    env.OAST_MAX_INTERACTIONS,
    DEFAULTS.maxInteractions,
    { min: 10, max: 10_000 },
    'OAST_MAX_INTERACTIONS',
    warnings
  )
  const dashboardLimit = parseInteger(
    env.OAST_DASHBOARD_LIMIT,
    Math.min(DEFAULTS.dashboardLimit, maxInteractions),
    { min: 1, max: 1000 },
    'OAST_DASHBOARD_LIMIT',
    warnings
  )
  const maxBodyBytes = parseInteger(
    env.OAST_MAX_BODY_BYTES,
    DEFAULTS.maxBodyBytes,
    { min: 1024, max: 1024 * 1024 },
    'OAST_MAX_BODY_BYTES',
    warnings
  )
  const requestTimeoutMs = parseInteger(
    env.OAST_REQUEST_TIMEOUT_MS,
    DEFAULTS.requestTimeoutMs,
    { min: 1000, max: 120_000 },
    'OAST_REQUEST_TIMEOUT_MS',
    warnings
  )
  const shutdownTimeoutMs = parseInteger(
    env.OAST_SHUTDOWN_TIMEOUT_MS,
    DEFAULTS.shutdownTimeoutMs,
    { min: 1000, max: 60_000 },
    'OAST_SHUTDOWN_TIMEOUT_MS',
    warnings
  )

  const config = {
    env: String(env.NODE_ENV || 'production'),
    host: String(env.OAST_HOST || DEFAULTS.host),
    port,
    publicUrl,
    // Callback URL origin as configured; also used to validate API-created URLs.
    publicOrigin: new URL(publicUrl).origin,
    maxInteractions,
    dashboardLimit,
    maxBodyBytes,
    requestTimeoutMs,
    shutdownTimeoutMs,
    logLevel,
    buildId: readBuildId(),
  }

  return { config, warnings }
}

module.exports = { loadConfig, DEFAULTS }
