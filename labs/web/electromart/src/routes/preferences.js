'use strict'

const router = require('express').Router()
const promo = require('../utils/promo')

/**
 * ============================================================
 *  Phase 1.3 — shop_preferences (LEGITIMATE, NOT vulnerable)
 * ============================================================
 *
 *  GET /preferences=:category  is the application's normal, discoverable way to
 *  choose how the homepage is ordered.  It sets a REAL browser cookie:
 *
 *        Set-Cookie: shop_preferences=<category>
 *
 *  e.g.  GET /preferences=phone   →  Set-Cookie: shop_preferences=phone
 *       GET /preferences=tv       →  Set-Cookie: shop_preferences=tv
 *       GET /preferences=none     →  Set-Cookie: shop_preferences=none
 *
 *  Only the supported category ids (or `none`) are accepted.  Anything else
 *  (typos, unrecognised values) falls back to the default `none`, so this
 *  mechanism can never be used to set an arbitrary cookie value — a deliberate
 *  server-side validation choice.  The preference is used ONLY for homepage
 *  ordering and is never reflected into an executable JavaScript context.
 */
// LAB-ONLY: persist the crafted `promo_ctx` produced by the documented parsing
// flaw, so the preference update also produces the intended browser-stored
// cookie-state transition (see the spec's Test D).
//
// Two entry points share the same interpretation:
//   • GET /preferences=:value          (legacy path form)
//   • GET /home?preferences=:value     (query form; implemented in routes/store.js)
//
// A normal value writes only `shop_preferences`. A crafted value such as
//
//        phone promo_ctx=<script>alert(1)<script>
//
// is ONE query value (a space does NOT delimit query parameters); the flawed
// parser separates the embedded `promo_ctx` token and applyPreferenceInput()
// re-issues ONLY that cookie. `promo_ctx_val` is never read from this input.
router.get('/preferences=:value', (req, res) => {
  const applied = promo.applyPreferenceInput(res, req.params.value)
  // Preserve the direct Cookie-header flavour of the same documented flaw
  // (e.g. an already-stored malformed shop_preferences) when the path value
  // itself was not the crafted form.
  if (!applied.flawTriggered) promo.applyPromoCtxTransition(res, req.headers.cookie)
  res.redirect('/home')
})

module.exports = router
