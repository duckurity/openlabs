'use strict'

const router = require('express').Router()
const bcrypt = require('bcryptjs')

const User = require('../models/user')
const config = require('../config')
const { requireAuth } = require('../middlewares/auth')
const { validateProfile, validatePasswordChange } = require('../utils/validate')

function renderProfile(res, { status, user, fieldErrors, generalError, passwordErrors }) {
  res.status(status || 200).render('profile', {
    user,
    fieldErrors: fieldErrors || {},
    generalError: generalError || null,
    passwordErrors: passwordErrors || {},
  })
}

async function findAccountUser(req) {
  return User.findById(req.session.user.id).exec()
}

function handleMissingAccount(req, res) {
  if (req.flash) req.flash('error', 'We could not find your account. Please log in again.')
  req.session.destroy(() => res.redirect('/login'))
}

/** ---------- Profile ---------- */

router.get('/profile', requireAuth, (req, res, next) => {
  findAccountUser(req)
    .then((user) => {
      if (!user) {
        handleMissingAccount(req, res)
        return
      }
      renderProfile(res, { user, fieldErrors: {}, passwordErrors: {} })
    })
    .catch(next)
})

/** Persistent profile updates: first name, last name, email, address. */
router.post('/profile', requireAuth, (req, res, next) => {
  const run = async () => {
    const user = await findAccountUser(req)
    if (!user) {
      handleMissingAccount(req, res)
      return
    }

    const { errors, value } = validateProfile(req.body || {})
    if (Object.keys(errors).length > 0) {
      return renderProfile(res, { status: 400, user, fieldErrors: errors })
    }

    user.email = value.email
    user.firstName = value.firstName
    user.lastName = value.lastName
    user.address = value.address

    try {
      await user.save()
    } catch (saveError) {
      if (
        saveError &&
        saveError.code === 11000 &&
        saveError.keyValue &&
        saveError.keyValue.email !== undefined
      ) {
        return renderProfile(res, {
          status: 409,
          user,
          fieldErrors: { email: 'This email is already used by another account.' },
        })
      }
      throw saveError
    }

    // Keep the session snapshot in sync with the saved account.
    req.session.user = { ...req.session.user, email: value.email, firstName: value.firstName }
    req.flash('success', 'Your profile has been updated.')
    res.redirect('/profile')
  }
  return run().catch(next)
})

/** ---------- Secure password change ---------- */

router.post('/profile/password', requireAuth, (req, res, next) => {
  const run = async () => {
    const user = await User.findOne({ _id: req.session.user.id }).select('+password').exec()
    if (!user) {
      handleMissingAccount(req, res)
      return
    }

    const body = req.body || {}
    const { errors } = validatePasswordChange(body)

    // Verify the current password before accepting the change.
    if (!errors.current_password && !(await user.comparePassword(body.current_password))) {
      errors.current_password = 'Your current password is incorrect.'
    }

    if (Object.keys(errors).length > 0) {
      return renderProfile(res, { status: 400, user, passwordErrors: errors })
    }

    user.password = await bcrypt.hash(String(body.new_password), config.bcryptRounds)
    await user.save()

    req.flash('success', 'Your password has been changed. Use it the next time you log in.')
    res.redirect('/profile')
  }
  return run().catch(next)
})

module.exports = router
