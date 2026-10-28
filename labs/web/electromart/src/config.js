'use strict'

/**
 * Centralised application configuration.
 * All values come from environment variables with safe, documented defaults.
 */

function toBool(value, fallback = false) {
  if (value === undefined || value === null || value === '') return fallback
  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase())
}

/**
 * Build a MongoDB URI from parts so usernames/passwords with special
 * characters (e.g. '#', '@', ':') are always percent-encoded correctly.
 * An explicit MONGO_URL in the environment always takes precedence.
 */
function buildMongoUrl() {
  const host = process.env.MONGO_HOST || '127.0.0.1'
  const port = process.env.MONGO_PORT || '27017'
  const db = process.env.MONGO_DB || 'electromart'
  const username = process.env.MONGO_USERNAME
  const password = process.env.MONGO_PASSWORD
  if (username && password) {
    return `mongodb://${encodeURIComponent(username)}:${encodeURIComponent(password)}@${host}:${port}/${db}?authSource=admin`
  }
  return `mongodb://${host}:${port}/${db}`
}

const maxAge = Number(process.env.SESSION_MAX_AGE)

const config = {
  env: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT) || 3000,
  // Lab reset on boot (default ON): wipe user-generated data (extra accounts,
  // carts, user reviews, stale sessions) and any completed takeover, then let
  // seed() rebuild the 20 products + the original victim. This makes every
  // "reset the Docker" method yield a pristine lab where a new user can always
  // register. Set LAB_RESET_ON_BOOT=false to persist data across restarts.
  resetOnBoot: toBool(process.env.LAB_RESET_ON_BOOT, true),
  // Helmet's CSP enables upgrade-insecure-requests by default. It is correct
  // behind HTTPS but breaks an HTTP-only deployment on a non-loopback host
  // (the browser rewrites subresources and form posts to https://). Compose
  // disables it explicitly for the internal HTTP lab.
  cspUpgradeInsecureRequests: toBool(process.env.CSP_UPGRADE_INSECURE_REQUESTS, true),
  mongoUrl: process.env.MONGO_URL || buildMongoUrl(),
  session: {
    name: process.env.SESSION_NAME || 'electromart.sid',
    secret: process.env.SESSION_SECRET || '',
    secure: toBool(process.env.SESSION_SECURE, false),
    // Default: 7 days.
    maxAge: maxAge > 0 ? maxAge : 7 * 24 * 60 * 60 * 1000,
  },
  // bcrypt work factor. Capped to stay responsive while remaining strong.
  bcryptRounds: (() => {
    const rounds = Number(process.env.BCRYPT_ROUNDS)
    if (!Number.isFinite(rounds) || rounds < 10) return 12
    return Math.min(Math.floor(rounds), 15)
  })(),
}

module.exports = config
