'use strict'

const router = require('express').Router()
const { requireAuth } = require('../middlewares/auth')
const { PLACEHOLDER_CATEGORIES } = require('../data/categories')

/**
 * Authenticated homepage (store).
 * Phase 1: navigation, profile link, logout, and disabled placeholder
 * controls for search / category / price sorting. No products yet —
 * the catalog arrives in Phase 2.
 */
router.get('/home', requireAuth, (req, res) => {
  const user = req.session.user
  res.render('home', {
    user,
    greetingName: (user.firstName || '').trim() || user.username,
    categories: PLACEHOLDER_CATEGORIES,
  })
})

module.exports = router
