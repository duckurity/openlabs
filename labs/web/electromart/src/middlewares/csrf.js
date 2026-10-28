'use strict'

const crypto = require('crypto')

/** Generate a cryptographically safe per-session CSRF token. */
function newCsrfToken() {
  return crypto.randomBytes(32).toString('hex')
}

function timingSafeEqualStrings(a, b) {
  const bufferA = Buffer.from(String(a), 'utf8')
  const bufferB = Buffer.from(String(b), 'utf8')
  if (bufferA.length !== bufferB.length) return false
  return crypto.timingSafeEqual(bufferA, bufferB)
}

/**
 * Verify the per-session CSRF token on every POST request.
 * Tokens are rendered into every form as a hidden `csrf_token` field.
 */
function attachCsrf(req, res, next) {
  if (req.method !== 'POST') return next()

  const expected = req.session && req.session.csrfToken
  const provided = req.body ? String(req.body.csrf_token === undefined || req.body.csrf_token === null ? '' : req.body.csrf_token) : ''

  if (!expected || provided.length === 0 || !timingSafeEqualStrings(expected, provided)) {
    return res
      .status(403)
      .render('error', {
        code: 403,
        message: 'That form request was not valid. Please go back, reload the page, and try again.',
      })
  }
  return next()
}

module.exports = { attachCsrf, newCsrfToken }
