'use strict'

const router = require('express').Router()
const bcrypt = require('bcryptjs')

const User = require('../models/user')
const config = require('../config')
const { guestOnly } = require('../middlewares/auth')
const { startAuthenticatedSession } = require('../middlewares/session')
const { validateRegistration } = require('../utils/validate')
const promo = require('../utils/promo')

/**
 * Phase 1.3 — after the FIRST login, default the ordering preference cookie to
 * `none` only when the client does not already carry a `shop_preferences`
 * cookie (so a returning user keeps their existing preference).
 */
function sendDefaultPreference(req, res) {
  const headerHadPreference = promo
    .loadCookies(req.headers.cookie)
    .parsedPairs.some((pair) => pair.startsWith(`${promo.COOKIES.PREFERENCES.name}=`))
  if (headerHadPreference) return // returning user keeps their existing preference
  res.cookie(promo.COOKIES.PREFERENCES.name, promo.COOKIES.PREFERENCES.defaultValue, {
    path: '/',
    httpOnly: false,
    sameSite: 'lax',
    maxAge: 30 * 24 * 60 * 60 * 1000,
  })
}

/** ---------- Registration ---------- */

router.get('/register', guestOnly, (req, res) => {
  res.render('register', {
    fieldErrors: {},
    generalError: null,
    values: { username: '', email: '', first_name: '', last_name: '' },
    promotion: promo.resolvePromotion(req.headers.cookie),
  })
})

router.post('/register', (req, res, next) => {
  const run = async () => {
    const { errors, value } = validateRegistration(req.body || {})
    if (Object.keys(errors).length > 0) {
      return res.status(400).render('register', { fieldErrors: errors, generalError: null, values: value })
    }

    try {
      const passwordHash = await bcrypt.hash(value.password, config.bcryptRounds)
      const user = await User.create({
        username: value.username,
        email: value.email,
        password: passwordHash,
        firstName: value.firstName,
        lastName: value.lastName,
      })

      return startAuthenticatedSession(req, user, (sessionError) => {
        if (sessionError) return next(sessionError)
        sendDefaultPreference(req, res)
        req.flash('success', `Welcome to ElectroMart, ${user.username}! Your account is ready.`)
        res.redirect('/home')
      })
    } catch (error) {
      // Duplicate username/email (unique index violation).
      if (error && error.code === 11000) {
        const fieldErrors = {}
        const keyValue = (error && error.keyValue) || {}
        if (keyValue.username !== undefined) fieldErrors.username = 'That username is already taken.'
        if (keyValue.email !== undefined) fieldErrors.email = 'An account with this email already exists.'
        if (Object.keys(fieldErrors).length === 0) fieldErrors.username = 'That username or email is already taken.'
        return res.status(409).render('register', { fieldErrors, generalError: null, values: value })
      }
      throw error
    }
  }
  return run().catch(next)
})

/** ---------- Login ---------- */

router.get('/login', guestOnly, (req, res) => {
  res.render('login', {
    fieldErrors: {},
    generalError: null,
    values: { username: '' },
    promotion: promo.resolvePromotion(req.headers.cookie),
  })
})

router.post('/login', (req, res, next) => {
  const run = async () => {
    const body = req.body || {}
    const username = String(body.username === undefined || body.username === null ? '' : body.username).trim().toLowerCase()
    const password = String(body.password === undefined || body.password === null ? '' : body.password)

    if (!username || !password) {
      const fieldErrors = {}
      if (!username) fieldErrors.username = 'Username is required.'
      if (!password) fieldErrors.password = 'Password is required.'
      return res.status(400).render('login', { fieldErrors, generalError: null, values: { username }, promotion: promo.resolvePromotion(req.headers.cookie) })
    }

    // Single generic error: we never reveal which part was wrong.
    const user = await User.findOne({ username }).select('+password').exec()
    const passwordOk = user ? await user.comparePassword(password) : false
    if (!user || !passwordOk) {
      return res.status(401).render('login', {
        fieldErrors: {},
        generalError: 'Invalid username or password.',
        values: { username },
        promotion: promo.resolvePromotion(req.headers.cookie),
      })
    }

    return startAuthenticatedSession(req, user, (sessionError) => {
      if (sessionError) return next(sessionError)
      sendDefaultPreference(req, res)
      req.flash('success', `Welcome back, ${user.username}!`)
      res.redirect('/home')
    })
  }
  return run().catch(next)
})

/** ---------- Logout (full session invalidation) ---------- */

router.post('/logout', (req, res) => {
  const finish = () => {
    res.clearCookie(config.session.name, { path: '/' })
    res.redirect('/?notice=logged_out')
  }

  if (req.session) {
    // destroy() deletes the server-side session document, so the old
    // session cookie no longer grants access anywhere.
    return req.session.destroy((error) => {
      if (error) console.error('[auth] session destroy failed:', error)
      finish()
    })
  }
  finish()
})

module.exports = router
