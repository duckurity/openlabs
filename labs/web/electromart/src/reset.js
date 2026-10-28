'use strict'

const { connectWithRetry, mongoose } = require('./db')

const User = require('./models/user')
const Product = require('./models/product')
const Review = require('./models/review')
const Cart = require('./models/cart')
const { VICTIM, restoreVictim } = require('./seed-victim')

/**
 * ============================================================
 *  Lab reset — restore the ElectroMart lab to its INITIAL state
 * ============================================================
 *
 * This is an account-takeover lab: an attacker registers a FRESH
 * account, abuses the XSS sink, and takes over the documented
 * VICTIM account.  To replay the exercise the lab has to return to
 * "day one":
 *
 *   • the 20 seeded products + their source reviews
 *   • the pristine VICTIM account (documented password + flag)
 *   • and NOTHING the attacker ever created:
 *       – no extra user accounts  → so re-registering a username never
 *         fails with "That username is already taken."
 *       – no attacker carts
 *       – no attacker-posted reviews
 *       – no stale login sessions
 *
 * resetLab() clears every user-generated / lab-mutable collection but KEEPS
 * the victim account: all other users, carts, user reviews and sessions are
 * removed, and the victim row is then restored in place to its documented
 * password + flag (undoing a completed takeover). The idempotent seed()
 * (called right after) rebuilds the stable product/review seed data.
 *
 * Why this runs on boot (see server.js / `LAB_RESET_ON_BOOT`): it makes
 * every "reset the Docker" method work identically —
 *   `docker compose down -v && up`, a plain `docker compose down && up`,
 * or even `docker compose restart` — a fresh boot is always a clean lab.
 */

/**
 * Clear all user-generated / mutable lab state so the next seed() leaves a
 * pristine "day one" state, while preserving the victim account.
 *
 * Only accounts OTHER than the victim are deleted; the victim row is kept and
 * reset to its documented contents by restoreVictim(). This guarantees that a
 * username registered by an attacker is always free again after a reset, and
 * that the victim keeps its documented credentials/flag. Idempotent and safe to
 * call repeatedly; it never throws on an absent collection and leaves indexes
 * intact (deleteMany, not dropCollection).
 *
 * @returns {Promise<{users: number, carts: number, reviews: number, products: number, sessions: number, victim: string|null}>}
 */
async function resetLab() {
  const db = mongoose.connection.db
  const sessions = db.collection('sessions') // connect-mongo session store

  // Clear in FK-flavoured order. There are no hard Mongo FKs, but clearing
  // dependants before the principals keeps counts intuitive. The victim is the
  // single user document that survives (matched by its unique email).
  const [sessionsRes, cartsRes, reviewsRes, usersRes, productsRes] = await Promise.all([
    sessions.deleteMany({}),
    Cart.deleteMany({}),
    Review.deleteMany({}),
    User.deleteMany({ email: { $ne: VICTIM.email } }),
    Product.deleteMany({}),
  ])

  // Put the surviving (or newly created) victim back to its pristine state.
  const victim = await restoreVictim()

  const summary = {
    sessions: sessionsRes.deletedCount,
    carts: cartsRes.deletedCount,
    reviews: reviewsRes.deletedCount,
    users: usersRes.deletedCount,
    products: productsRes.deletedCount,
    victim: victim.username,
  }
  console.log(
    `[reset] Lab restored to day-one state — removed ${usersRes.deletedCount} non-victim user(s), ` +
      `${cartsRes.deletedCount} cart(s), ${reviewsRes.deletedCount} review(s), ` +
      `${productsRes.deletedCount} product(s), ${sessionsRes.deletedCount} stale session(s); ` +
      `victim "${victim.username}" preserved and restored.`
  )
  return summary
}

// Run standalone (node src/reset.js) or `npm run reset`:
// wipe the lab and immediately rebuild the pristine "day one" state.
if (require.main === module) {
  const { seed } = require('./seed')
  connectWithRetry()
    .then(() => resetLab())
    .then(() => seed())
    .then(() => mongoose.disconnect().then(() => process.exit(0)).catch(() => process.exit(0)))
    .catch((err) => {
      console.error('[reset] failed:', err)
      process.exit(1)
    })
}

module.exports = { resetLab }
