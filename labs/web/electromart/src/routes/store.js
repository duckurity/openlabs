'use strict'

const router = require('express').Router()
const Product = require('../models/product')
const Review = require('../models/review')
const Cart = require('../models/cart')
const { requireAuth } = require('../middlewares/auth')
const promo = require('../utils/promo')

// ---------- Helpers ----------
function buildQuery(req) {
  const filter = {}
  if (req.query.category && req.query.category !== 'all') {
    filter.category = req.query.category
  }
  if (req.query.q && String(req.query.q).trim()) {
    const q = String(req.query.q).trim()
    const rx = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')
    filter.$or = [{ name: rx }, { brand: rx }, { model: rx }]
  }
  return filter
}

function buildSort(req) {
  if (req.query.sort === 'price-asc') return { price: 1 }
  if (req.query.sort === 'price-desc') return { price: -1 }
  return { name: 1 }
}

async function getCartCount(userId) {
  if (!userId) return 0
  const cart = await Cart.findOne({ user: userId }).exec()
  return cart ? cart.items.reduce((s, i) => s + i.quantity, 0) : 0
}

const CATEGORIES = [
  { id: 'phone', label: 'Phones' },
  { id: 'TV', label: 'TVs' },
  { id: 'washing machine', label: 'Washing Machines' },
  { id: 'stove', label: 'Stoves' },
  { id: 'blender', label: 'Blenders' },
  { id: 'AC', label: 'Air Conditioners' },
  { id: 'water filter', label: 'Water Filters' },
]

// ============================================================
//  CART (must come before /product/:slug)
// ============================================================

router.get('/cart', requireAuth, async (req, res, next) => {
  try {
    const cart = await Cart.findOne({ user: req.session.user.id }).exec()
    const items = cart ? cart.items : []
    const subtotal = items.reduce((s, i) => s + i.price * i.quantity, 0)
    const totalItems = items.reduce((s, i) => s + i.quantity, 0)
    res.render('cart', { items, subtotal, totalItems, user: req.session.user, cartCount: totalItems, categories: CATEGORIES })
  } catch (err) { next(err) }
})

router.post('/cart/remove', requireAuth, (req, res, next) => {
  const run = async () => {
    const slug = String(req.body.slug || '').trim().toLowerCase()
    if (!slug) { req.flash('error', 'Invalid item.'); return res.redirect('/cart') }
    const cart = await Cart.findOne({ user: req.session.user.id }).exec()
    if (cart) {
      cart.items = cart.items.filter(i => i.productSlug !== slug)
      await cart.save()
    }
    req.flash('success', 'Item removed from cart.')
    res.redirect('/cart')
  }
  return run().catch(next)
})

router.post('/cart/update', requireAuth, (req, res, next) => {
  const run = async () => {
    const slug = String(req.body.slug || '').trim().toLowerCase()
    const qty = Math.min(Math.max(parseInt(req.body.quantity, 10) || 1, 1), 99)
    const cart = await Cart.findOne({ user: req.session.user.id }).exec()
    if (cart) {
      const item = cart.items.find(i => i.productSlug === slug)
      if (item) {
        item.quantity = qty
        await cart.save()
      }
    }
    req.flash('success', 'Cart updated.')
    res.redirect('/cart')
  }
  return run().catch(next)
})

// ============================================================
//  PRODUCT DETAIL
// ============================================================

router.get('/product/:slug', requireAuth, async (req, res, next) => {
  try {
    const slug = String(req.params.slug).trim().toLowerCase()
    const [product, reviews] = await Promise.all([
      Product.findOne({ slug }).exec(),
      Review.find({ productSlug: slug }).sort({ createdAt: -1 }).limit(50).exec(),
    ])
    if (!product) {
      return res.status(404).render('error', { code: 404, message: 'Product not found.' })
    }

    // Phase 1.3 — preference learning: viewing a product records interest in
    // its category by setting the LEGITIMATE shop_preferences ordering cookie.
    // The value is a server-side category id (always a supported preference)
    // and this cookie is never reflected into JS, so it stays non-vulnerable.
    // Browsing a phone and returning home now shows phones first.
    if (promo.SUPPORTED_PREFERENCES.includes(product.category)) {
      res.cookie('shop_preferences', product.category, {
        path: '/',
        httpOnly: false,
        sameSite: 'lax',
        maxAge: 30 * 24 * 60 * 60 * 1000,
      })
    }
    // LAB-ONLY: when the crafted preference input reaches this legitimate
    // shop_preferences-update point, the documented parsing flaw also yields an
    // attacker-controlled promo_ctx. Persist it here (and only here) so BOTH
    // preference-update entry points produce the intended browser-stored state
    // transition. promo_ctx_val is never touched.
    promo.applyPromoCtxTransition(res, req.headers.cookie)

    const cartCount = await getCartCount(req.session.user.id)
    res.render('product', {
      product, reviews, cartCount, user: req.session.user,
      avatarInitial: res.locals.avatarInitial, csrfToken: res.locals.csrfToken,
      categories: CATEGORIES,
      reviewErrors: {}, reviewSubmitted: false,
    })
  } catch (err) { next(err) }
})

router.post('/product/:slug/reviews', requireAuth, (req, res, next) => {
  const run = async () => {
    const slug = String(req.params.slug).trim().toLowerCase()
    const product = await Product.findOne({ slug }).exec()
    if (!product) { req.flash('error', 'Product not found.'); return res.redirect('/home') }

    const body = req.body || {}
    const rating = parseInt(body.rating, 10)
    const comment = String(body.comment === undefined || body.comment === null ? '' : body.comment).trim().slice(0, 2000)

    const errors = {}
    if (isNaN(rating) || rating < 1 || rating > 5) errors.rating = 'Please select a rating from 1 to 5 stars.'
    if (!comment) errors.comment = 'Please write a comment.'
    else if (comment.length < 5) errors.comment = 'Comment must be at least 5 characters.'

    if (Object.keys(errors).length > 0) {
      const reviews = await Review.find({ productSlug: slug }).sort({ createdAt: -1 }).limit(50).exec()
      const cartCount = await getCartCount(req.session.user.id)
      return res.status(400).render('product', {
        product, reviews, cartCount, user: req.session.user,
        avatarInitial: res.locals.avatarInitial, csrfToken: res.locals.csrfToken,
        categories: CATEGORIES, reviewErrors: errors, reviewSubmitted: false,
        submittedComment: comment, submittedRating: isNaN(rating) ? '' : String(rating),
      })
    }

    const displayName = String(req.session.user.firstName || '').trim() || req.session.user.username || 'Customer'
    await Review.create({
      productSlug: slug, author: displayName, rating, comment,
      userName: req.session.user.username, isAuthor: false,
    })

    // Update product average rating
    const stats = await Review.aggregate([
      { $match: { productSlug: slug } },
      { $group: { _id: null, avg: { $avg: '$rating' } } },
    ])
    if (stats.length > 0) {
      product.rating = Math.round(stats[0].avg * 10) / 10
      await product.save()
    }

    req.flash('success', 'Thank you! Your review has been submitted.')
    res.redirect('/product/' + slug)
  }
  return run().catch(next)
})

router.post('/product/:slug/add-to-cart', requireAuth, (req, res, next) => {
  const run = async () => {
    const slug = String(req.params.slug).trim().toLowerCase()
    const product = await Product.findOne({ slug }).exec()
    if (!product) { req.flash('error', 'Product not found.'); return res.redirect('/home') }
    if (product.stock <= 0) { req.flash('error', 'Sorry, this item is currently out of stock.'); return res.redirect('/product/' + slug) }

    const qty = Math.min(Math.max(parseInt(req.body.quantity, 10) || 1, 1), Math.min(99, product.stock))
    const userId = req.session.user.id

    let cart = await Cart.findOne({ user: userId }).exec()
    if (!cart) cart = await Cart.create({ user: userId, items: [] })

    const existingItem = cart.items.find(i => i.productSlug === slug)
    if (existingItem) {
      existingItem.quantity = Math.min(existingItem.quantity + qty, 99, product.stock)
      existingItem.stock = product.stock
    } else {
      cart.items.push({
        productSlug: slug, name: product.name, brand: product.brand,
        price: product.price, image: product.image, quantity: qty, stock: product.stock,
      })
    }
    await cart.save()

    req.flash('success', `Added ${qty} × ${product.name} to your cart.`)
    res.redirect('/cart')
  }
  return run().catch(next)
})

// ============================================================
//  HOME PAGE (catalog with search, filter, sort)
// ============================================================

router.get('/home', requireAuth, async (req, res, next) => {
  try {
    const filter = buildQuery(req)
    const sort = buildSort(req)

    const [total, products] = await Promise.all([
      Product.countDocuments(filter),
      Product.find(filter).sort(sort).limit(100).exec(),
    ])

    // Compute review avg per product for cards
    const slugs = products.map(p => p.slug)
    const reviewStats = slugs.length
      ? await Review.aggregate([
          { $match: { productSlug: { $in: slugs } } },
          { $group: { _id: '$productSlug', count: { $sum: 1 }, avg: { $avg: '$rating' } } },
        ])
      : []
    const reviewMap = {}
    for (const rc of reviewStats) reviewMap[rc._id] = { count: rc.count, avg: Math.round(rc.avg * 10) / 10 }

    const cartCount = await getCartCount(req.session.user.id)
    const user = req.session.user
    const greetingName = (user.firstName || '').trim() || user.username

    const activeQ = req.query.q ? String(req.query.q).trim() : ''
    const activeCategory = req.query.category && req.query.category !== 'all' ? req.query.category : ''
    const activeSort = req.query.sort || ''

    // Phase 1.3 — explicit preference-selection on the homepage:
    //   GET /home?preferences=phone
    // updates the REAL shop_preferences cookie through the normal response.
    // A crafted value containing an embedded whitespace-separated
    // `promo_ctx=...` token exercises the documented parser flaw and also
    // re-issues promo_ctx; promo_ctx_val is never touched.
    let selectedPreference = null
    let appliedPreference = null
    if (typeof req.query.preferences === 'string') {
      appliedPreference = promo.applyPreferenceInput(res, req.query.preferences)
      selectedPreference = appliedPreference.category
    } else {
      // Preserve the Cookie-header flavour of the same documented flaw: if the
      // browser already carries a malformed shop_preferences value, the next
      // applicable request re-syncs the attacker-controlled promo_ctx cookie.
      promo.applyPromoCtxTransition(res, req.headers.cookie)
    }

    // Phase 1.3 — the legitimate shop_preferences cookie (never reflected into JS).
    // The current query selection wins for this render; otherwise use the cookie
    // the BROWSER sent. A response cookie is not available to this same request.
    const preference = selectedPreference !== null
      ? selectedPreference
      : promo.loadCookies(req.headers.cookie).preferences

    // shop_preferences drives homepage ordering ONLY for the plain catalog view.
    // An active search, category filter, or price sort overrides it; "Clear"
    // restores it. It never hides products — it only moves the preferred
    // category to the front.
    const hasExplicitFilter = Boolean(activeQ) || Boolean(activeCategory) || Boolean(activeSort)
    const ordered = hasExplicitFilter ? products : promo.orderProductsByPreference(products, preference)

    // Phase 1.3 — promotion values for the banner + ordering preference.
    // A crafted ?preferences= value that carried an embedded promo_ctx must be
    // visible in THIS response too (a Set-Cookie is not readable until the next
    // request), so the banner matches the cookie the browser is about to store.
    const promotion = promo.resolvePromotion(req.headers.cookie)
    if (appliedPreference && appliedPreference.flawTriggered && appliedPreference.injectedPromoCtx !== null) {
      promotion.promoContext = appliedPreference.injectedPromoCtx
    }

    res.render('home', {
      user, greetingName, products: ordered.map(p => ({
        ...p.toObject(),
        reviewCount: reviewMap[p.slug] ? reviewMap[p.slug].count : 0,
        avgRating: reviewMap[p.slug] ? reviewMap[p.slug].avg : p.rating,
      })),
      total, categories: CATEGORIES,
      activeQ,
      activeCategory,
      activeSort,
      cartCount,
      preference,
      promotion,
      hasExplicitFilter,
    })
  } catch (err) { next(err) }
})

module.exports = router
