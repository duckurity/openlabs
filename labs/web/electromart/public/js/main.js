/* ============================================================
   ElectroMart — client-side validation (fast UX feedback only)
   The server re-validates everything on every request; this code
   never replaces the server-side checks.
   ============================================================ */
(function () {
  'use strict'

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  var USERNAME_RE = /^[a-z0-9_]{3,30}$/

  function fieldOf(form, name) {
    var input = form.querySelector('[name="' + name + '"]')
    return input ? input.closest('.field') : null
  }

  function markError(form, name, message) {
    var field = fieldOf(form, name)
    if (!field) return
    field.classList.add('field--invalid')
    var errorEl = field.querySelector('.field-error')
    if (!errorEl) {
      errorEl = document.createElement('p')
      errorEl.className = 'field-error'
      field.appendChild(errorEl)
    }
    errorEl.textContent = message
    errorEl.hidden = false
  }

  function clearForm(form) {
    form.querySelectorAll('.field-error').forEach(function (el) {
      el.textContent = ''
      el.hidden = true
    })
    form.querySelectorAll('.field--invalid').forEach(function (el) {
      el.classList.remove('field--invalid')
    })
  }

  function check(form, name, message) {
    if (message) {
      markError(form, name, message)
      return false
    }
    return true
  }

  function value(form, name) {
    var el = form.querySelector('[name="' + name + '"]')
    return el ? String(el.value).trim() : ''
  }

  function raw(form, name) {
    var el = form.querySelector('[name="' + name + '"]')
    return el ? String(el.value) : ''
  }

  function validate(form) {
    var kind = form.getAttribute('data-validate')
    var ok = true

    if (kind === 'register') {
      var username = value(form, 'username')
      ok &= check(form, 'username', !username ? 'Username is required.'
        : username.length < 3 ? 'Username must be at least 3 characters.'
        : !USERNAME_RE.test(username) ? 'Use 3–30 characters: letters, numbers, or underscores only.'
        : null)
      ok &= check(form, 'email', !value(form, 'email') ? 'Email address is required.'
        : !EMAIL_RE.test(value(form, 'email')) ? 'Enter a valid email address, like name@example.com.'
        : null)
      var password = raw(form, 'password')
      ok &= check(form, 'password', !password ? 'Create a password.'
        : password.length < 8 ? 'Password must be at least 8 characters.'
        : password.length > 72 ? 'Password must be 72 characters or fewer.'
        : null)
      ok &= check(form, 'confirm_password',
        password && password.length >= 8 && password !== raw(form, 'confirm_password')
          ? 'Passwords do not match.' : null)
    }

    if (kind === 'login') {
      ok &= check(form, 'username', !value(form, 'username') ? 'Username is required.' : null)
      ok &= check(form, 'password', !raw(form, 'password') ? 'Password is required.' : null)
    }

    if (kind === 'profile') {
      ok &= check(form, 'email', !value(form, 'email') ? 'Email address is required.'
        : !EMAIL_RE.test(value(form, 'email')) ? 'Enter a valid email address, like name@example.com.'
        : null)
      ok &= check(form, 'address', value(form, 'address').length > 500 ? 'Delivery address must be 500 characters or fewer.' : null)
    }

    if (kind === 'password') {
      ok &= check(form, 'current_password', !raw(form, 'current_password') ? 'Enter your current password.' : null)
      var next = raw(form, 'new_password')
      ok &= check(form, 'new_password', !next ? 'Enter a new password.'
        : next.length < 8 ? 'New password must be at least 8 characters.'
        : next.length > 72 ? 'New password must be 72 characters or fewer.'
        : null)
      ok &= check(form, 'new_password_confirmation',
        next.length >= 8 && next !== raw(form, 'new_password_confirmation') ? 'Passwords do not match.' : null)
    }

    if (kind === 'review') {
      var rating = value(form, 'rating')
      ok &= check(form, 'rating', !rating ? 'Please select a rating.' : null)
      var comment = value(form, 'comment')
      ok &= check(form, 'comment', !comment ? 'Please write a comment.'
        : comment.length < 5 ? 'Comment must be at least 5 characters.' : null)
    }

    return Boolean(ok)
  }

  document.addEventListener('submit', function (event) {
    var form = event.target
    if (!form || !form.matches || !form.matches('form[data-validate]')) return
    clearForm(form)
    if (!validate(form)) {
      event.preventDefault()
      var first = form.querySelector('.field-error:not([hidden])')
      if (first) {
        var field = first.closest('.field')
        var input = field && field.querySelector('input, select, textarea')
        if (input && input.focus) input.focus()
      }
    }
  }, true)

  /* Quantity increment / decrement buttons */
  document.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-qty-action]')
    if (!btn) return
    var control = btn.closest('.qty-control')
    if (!control) return
    var input = control.querySelector('.qty-input')
    if (!input) return
    var min = parseInt(input.getAttribute('min'), 10) || 1
    var max = parseInt(input.getAttribute('max'), 10) || 99
    var current = parseInt(input.value, 10) || min
    var delta = btn.getAttribute('data-qty-action') === 'inc' ? 1 : -1
    var next = Math.min(max, Math.max(min, current + delta))
    input.value = next
  })
})()
