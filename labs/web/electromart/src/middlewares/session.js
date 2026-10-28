'use strict'

const crypto = require('crypto')

/**
 * Start a fresh, authenticated session for the given user.
 *
 * The session is regenerated (prevents session fixation) and a new CSRF
 * token is issued for the new session.
 */
function startAuthenticatedSession(req, user, callback) {
  req.session.regenerate((regenerateError) => {
    if (regenerateError) {
      if (callback) return callback(regenerateError)
      console.error('[session] regenerate failed:', regenerateError)
      return
    }
    req.session.csrfToken = crypto.randomBytes(32).toString('hex')
    req.session.flash = null
    req.session.user = {
      id: user._id.toString(),
      username: user.username,
      email: user.email,
      firstName: user.firstName || '',
    }
    if (callback) callback(null)
  })
}

module.exports = { startAuthenticatedSession }
