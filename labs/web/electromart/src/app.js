'use strict'

const path = require('path')

const express = require('express')
const session = require('express-session')
const MongoStore = require('connect-mongo')
const helmet = require('helmet')

const config = require('./config')
const { newCsrfToken, attachCsrf } = require('./middlewares/csrf')
const { notFound, errorHandler } = require('./middlewares/errors')
const { renderReviewComment } = require('./utils/review-link')

const FALLBACK_SECRET = 'electromart-insecure-development-fallback-please-set-SESSION_SECRET'

/** Build the Express application (kept separate from server.js for testability). */
function createApp() {
  const app = express()

  app.disable('x-powered-by')
  app.set('view engine', 'ejs')
  app.set('views', path.join(__dirname, '..', 'views'))

  // Sessions persist in MongoDB (the `sessions` collection), so logins
  // survive app restarts and logout fully invalidates the session.
  const store = MongoStore.create({
    mongoUrl: config.mongoUrl,
    collectionName: 'sessions',
  })

  // Security headers + Content-Security-Policy.
  //
  // Phase 1.3 note: the XSS lab relies on TWO intentionally inline <script>
  // blocks that embed `window.electroMart` (the promo-context sink) on the home
  // and login pages. To let that reflected XSS *execute* (as the exercise
  // requires), script-src permits 'unsafe-inline'.
  //
  //   • This is the single, documented reason the policy is relaxed; only the
  //     home and login templates emit an inline <script>, so every other page
  //     is unaffected.
  //   • It is a LAB-ONLY relaxation. A real store would REMOVE 'unsafe-inline'
  //     (strict nonce/hash policy) AND escape the promo value (see README →
  //     Remediation). Do not replicate this in production.
  app.use(
    helmet({
      contentSecurityPolicy: {
        useDefaults: true,
        directives: {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'unsafe-inline'"],
          'style-src': ["'self'"],
          'img-src': ["'self'", 'data:'],
          // LAB-ONLY: allow fetch()/sendBeacon() to any origin on every page.
          // This intentionally removes the OAST-specific allowlist so a
          // reflected payload is not restricted to a single callback host.
          // Do not copy this into production.
          'connect-src': ['*'],
          'font-src': ["'self'"],
          'object-src': ["'none'"],
          'frame-ancestors': ["'none'"],
          'base-uri': ["'self'"],
          'form-action': ["'self'"],
          'upgrade-insecure-requests': config.cspUpgradeInsecureRequests ? [] : null,
        },
      },
      crossOriginEmbedderPolicy: false,
    })
  )

  app.use(express.urlencoded({ extended: true, limit: '100kb' }))
  app.use(express.json({ limit: '100kb' }))
  app.use(express.static(path.join(__dirname, '..', 'public'), { maxAge: '1h', index: false }))
  // Product images: served from the devices/ directory (image-only, no .txt files in production concern)
  app.use('/images', express.static(path.join(__dirname, '..', 'devices'), { maxAge: '1h', index: false }))

  app.use(
    session({
      name: config.session.name,
      secret: config.session.secret || FALLBACK_SECRET,
      store,
      resave: false,
      saveUninitialized: false,
      rolling: true,
      cookie: {
        httpOnly: true,
        sameSite: 'lax',
        secure: config.session.secure,
        maxAge: config.session.maxAge,
      },
    })
  )

  // Ensure a per-session CSRF token exists and expose it to templates.
  app.use((req, res, next) => {
    if (req.session && !req.session.csrfToken) {
      req.session.csrfToken = newCsrfToken()
    }
    if (req.session) res.locals.csrfToken = req.session.csrfToken
    next()
  })
  app.use(attachCsrf)

  // Flash messages: written to the session, shown once on the next render.
  app.use((req, res, next) => {
    const flash = req.session ? req.session.flash : null
    res.locals.flash = flash && flash.message ? flash : null
    if (flash && req.session) req.session.flash = null // persist the consumption
    req.flash = (type, message) => {
      if (req.session) req.session.flash = { type, message }
    }
    next()
  })

  // Safe review-comment link rendering is available to every view. The helper
  // escapes all comment text and only emits anchors for http(s) or site-relative
  // URLs; see src/utils/review-link.js.
  app.locals.renderReviewComment = renderReviewComment

  // Per-request locals shared by all views.
  app.use((req, res, next) => {
    const user = req.session && req.session.user
    res.locals.currentUser = user ? { ...user } : null
    res.locals.avatarInitial = user
      ? (String(user.firstName || user.username || '?').trim().charAt(0) || '?').toUpperCase()
      : ''
    res.locals.path = (req.originalUrl || '/').split('?')[0].split('#')[0]
    next()
  })

  // Lightweight liveness endpoint (used by the Docker healthcheck).
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'electromart', time: new Date().toISOString() })
  })

  // Routes
  app.use('/', require('./routes/public')) // GET /
  app.use('/', require('./routes/auth')) // GET/POST /register, /login, POST /logout
  app.use('/', require('./routes/preferences')) // GET /preferences=:value (sets shop_preferences)
  app.use('/', require('./routes/store')) // GET /home, /product/:slug, /cart, reviews, add-to-cart
  app.use('/', require('./routes/profile')) // GET /profile, POST /profile, POST /profile/password

  // 404 + central error handling
  app.use(notFound)
  app.use(errorHandler)

  return app
}

module.exports = { createApp, FALLBACK_SECRET }
