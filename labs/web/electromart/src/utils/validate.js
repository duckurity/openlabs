'use strict'

/**
 * Server-side validation helpers.
 *
 * These run on every request — the browser-side checks in
 * `public/js/main.js` are for feedback speed only and are never trusted.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const USERNAME_RE = /^[a-z0-9_]{3,30}$/

function cleanText(input, maxLength) {
  if (input === undefined || input === null) return ''
  return String(input).trim().slice(0, maxLength)
}

function rawString(input) {
  if (input === undefined || input === null) return ''
  return String(input)
}

function isValidEmail(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 254 && EMAIL_RE.test(value)
}

function isValidUsername(value) {
  return typeof value === 'string' && USERNAME_RE.test(value)
}

function isValidPassword(value) {
  return typeof value === 'string' && value.length >= 8 && value.length <= 72
}

function validateRegistration(body) {
  body = body || {}
  const errors = {}
  const value = {}

  const username = cleanText(body.username, 30).toLowerCase()
  if (!username) {
    errors.username = 'Username is required.'
  } else if (username.length < 3) {
    errors.username = 'Username must be at least 3 characters.'
  } else if (!isValidUsername(username)) {
    errors.username = 'Use 3–30 characters: letters, numbers, or underscores only.'
  } else {
    value.username = username
  }

  const email = cleanText(body.email, 254).toLowerCase()
  if (!email) {
    errors.email = 'Email address is required.'
  } else if (!isValidEmail(email)) {
    errors.email = 'Enter a valid email address, like name@example.com.'
  } else {
    value.email = email
  }

  const password = rawString(body.password)
  if (!password) {
    errors.password = 'Create a password.'
  } else if (password.length < 8) {
    errors.password = 'Password must be at least 8 characters.'
  } else if (password.length > 72) {
    errors.password = 'Password must be 72 characters or fewer.'
  } else {
    value.password = password
  }

  const confirm = rawString(body.confirm_password)
  if (value.password && confirm !== value.password) {
    errors.confirm_password = 'Passwords do not match.'
  }

  value.firstName = cleanText(body.first_name, 100)
  value.lastName = cleanText(body.last_name, 100)

  return { errors, value }
}

function validateProfile(body) {
  body = body || {}
  const errors = {}
  const value = {}

  const email = cleanText(body.email, 254).toLowerCase()
  if (!email) {
    errors.email = 'Email address is required.'
  } else if (!isValidEmail(email)) {
    errors.email = 'Enter a valid email address, like name@example.com.'
  } else {
    value.email = email
  }

  value.firstName = cleanText(body.first_name, 100)
  value.lastName = cleanText(body.last_name, 100)

  const addressRaw = rawString(body.address).trim()
  if (addressRaw.length > 500) {
    errors.address = 'Delivery address must be 500 characters or fewer.'
  } else {
    value.address = addressRaw
  }

  return { errors, value }
}

function validatePasswordChange(body) {
  body = body || {}
  const errors = {}

  const current = rawString(body.current_password)
  const next = rawString(body.new_password)
  const confirm = rawString(body.new_password_confirmation)

  if (!current) {
    errors.current_password = 'Enter your current password.'
  }

  if (!next) {
    errors.new_password = 'Enter a new password.'
  } else if (next.length < 8) {
    errors.new_password = 'New password must be at least 8 characters.'
  } else if (next.length > 72) {
    errors.new_password = 'New password must be 72 characters or fewer.'
  }

  if (next.length >= 8 && next !== confirm) {
    errors.new_password_confirmation = 'Passwords do not match.'
  }

  return { errors }
}

module.exports = {
  cleanText,
  isValidEmail,
  isValidUsername,
  isValidPassword,
  validateRegistration,
  validateProfile,
  validatePasswordChange,
}
