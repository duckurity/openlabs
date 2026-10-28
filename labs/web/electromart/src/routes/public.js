'use strict'

const router = require('express').Router()
const promo = require('../utils/promo')

/**
 * Initialise the two promo cookies on the FIRST welcome-page visit.
 *
 * The welcome page never renders these values — it only seeds them so a
 * returning browser carries a known `promo_ctx` / `promo_ctx_val`.  They are
 * issued ONLY when the request does not already carry that cookie, so:
 *
 *   • the first response carries `Set-Cookie` for both (visible in the
 *     browser's Network panel), and
 *   • a subsequent visit where the browser already sent the cookie (or an
 *     intentional lab-state change) is NOT reset — the value is persisted.
 *
 * `path: '/'` scopes them to the whole ElectroMart origin (Login, Home and
 * the preference pages all read them); `httpOnly: false` keeps the context
 * readable to the page's own JS — the deliberate lab choice.  The discount
 * default (`promo_ctx_val`) is fixed and independently validated later by
 * `safePromoValue`, never derived from any request input.
 */
function ensurePromoDefaults(req, res) {
  const header = req.headers.cookie
  const present = new Set()
  if (header) {
    for (const part of String(header).split(';')) {
      const name = part.split('=')[0].trim()
      if (name) present.add(name)
    }
  }
  if (!present.has(promo.COOKIES.PROMO_CTX.name)) {
    res.cookie(promo.COOKIES.PROMO_CTX.name, promo.COOKIES.PROMO_CTX.defaultValue, promo.promoCookieOptions(promo.COOKIES.PROMO_CTX.name))
  }
  if (!present.has(promo.COOKIES.PROMO_VAL.name)) {
    res.cookie(promo.COOKIES.PROMO_VAL.name, promo.COOKIES.PROMO_VAL.defaultValue, promo.promoCookieOptions(promo.COOKIES.PROMO_VAL.name))
  }
}

/** Public welcome page — no authentication required, no store navbar. */
router.get('/', (req, res) => {
  ensurePromoDefaults(req, res)
  const notice = req.query.notice === 'logged_out' ? 'logged_out' : null
  res.render('welcome', { notice })
})

module.exports = router
