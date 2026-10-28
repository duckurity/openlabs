'use strict'

const LEVELS = Object.freeze({ debug: 10, info: 20, warn: 30, error: 40 })

/**
 * Remove lab secrets from anything that may reach the log stream. Logging is
 * intentionally defensive: the bot never reads the victim address/flag, never
 * logs cookies/tokens, and this sanitiser is a second line of defence for
 * unexpected error text.
 */
function makeSanitizer(secrets) {
  const exactSecrets = (secrets || []).filter((secret) => typeof secret === 'string' && secret.length > 0)
  return function sanitize(value) {
    let text = String(value === undefined || value === null ? '' : value)
    for (const secret of exactSecrets) {
      text = text.split(secret).join('[redacted]')
    }
    text = text.replace(/duck\{[^}]{0,300}\}/g, '[redacted-flag]')
    text = text.replace(
      /((?:electromart\.sid|connect\.sid|promo_ctx|promo_ctx_val|shop_preferences)=)[^;\s,]+/gi,
      '$1[redacted]'
    )
    text = text.replace(
      /((?:password|passwd|pwd|token|cookie)\s*[=:]\s*)[^\s,;]+/gi,
      '$1[redacted]'
    )
    return text
  }
}

function createLogger({ level = 'info', secrets = [] } = {}) {
  const threshold = LEVELS[level] === undefined ? LEVELS.info : LEVELS[level]
  const sanitize = makeSanitizer(secrets)

  function sanitizeValue(value, depth = 0) {
    if (value === undefined) return undefined
    if (value === null || typeof value === 'number' || typeof value === 'boolean') {
      return value
    }
    if (typeof value === 'string') return sanitize(value)
    if (depth >= 3) return sanitize(String(value))
    if (Array.isArray(value)) return value.map((item) => sanitizeValue(item, depth + 1))
    if (typeof value === 'object') {
      const output = {}
      for (const [key, item] of Object.entries(value)) {
        if (item === undefined) continue
        output[sanitize(key)] = sanitizeValue(item, depth + 1)
      }
      return output
    }
    return sanitize(String(value))
  }

  function emit(levelName, event, meta = {}) {
    if (LEVELS[levelName] < threshold) return
    const entry = {
      ts: new Date().toISOString(),
      level: levelName,
      service: 'victim-bot',
      event,
    }
    for (const [key, value] of Object.entries(meta || {})) {
      const sanitized = sanitizeValue(value)
      if (sanitized !== undefined) entry[sanitize(key)] = sanitized
    }
    // A single JSON object per line is easy to grep/filter and avoids dumping
    // page content, headers, cookies or credentials.
    console.log(JSON.stringify(entry))
  }

  return {
    debug: (event, meta) => emit('debug', event, meta),
    info: (event, meta) => emit('info', event, meta),
    warn: (event, meta) => emit('warn', event, meta),
    error: (event, meta) => emit('error', event, meta),
    sanitize,
  }
}

function safeError(error, sanitize = String) {
  if (!error) return null
  const result = {
    name: error.name || 'Error',
    message: sanitize(error.message || String(error)),
  }
  if (error.category) result.category = sanitize(error.category)
  if (error.step) result.step = sanitize(error.step)
  if (error.code) result.code = sanitize(error.code)
  if (error.transient !== undefined) result.transient = Boolean(error.transient)
  return result
}

module.exports = { createLogger, safeError, makeSanitizer }
