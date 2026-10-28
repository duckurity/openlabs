'use strict'

/** Route guards for session-based authentication. */

function requireAuth(req, res, next) {
  if (req.session && req.session.user) return next()
  if (req.flash) req.flash('error', 'Please log in to continue.')
  return res.redirect('/login')
}

function guestOnly(req, res, next) {
  if (req.session && req.session.user) return res.redirect('/home')
  return next()
}

module.exports = { requireAuth, guestOnly }
