'use strict'

/**
 * ============================================================
 *  Lab reset — the victim survives, everything else is cleared
 * ============================================================
 *
 * Proves the "reset the Docker" contract at the database level:
 *
 *   • every account created by an attacker is deleted, so its username can be
 *     registered again (no more "That username is already taken.")
 *   • the victim account is KEPT (not deleted) and restored to its documented
 *     password / name / flag, undoing a completed takeover
 *   • carts, user reviews, seeded products and stale sessions are cleared
 *
 * Runs against a throwaway database and skips itself when MongoDB is not
 * reachable, so `npm test` still works on a machine without a database.
 */

const test = require('node:test')
const assert = require('node:assert/strict')
const bcrypt = require('bcryptjs')

const { mongoose } = require('../src/db')
const { resetLab } = require('../src/reset')
const User = require('../src/models/user')
const Product = require('../src/models/product')
const Review = require('../src/models/review')
const Cart = require('../src/models/cart')
const { VICTIM } = require('../src/seed-victim')

const TEST_MONGO_URL =
  process.env.RESET_TEST_MONGO_URL || 'mongodb://127.0.0.1:27017/electromart_reset_test'

function userDoc(username) {
  return {
    username,
    email: `${username}@example.test`,
    password: 'attacker-chosen-password',
    firstName: username,
    lastName: 'Tester',
  }
}

test('resetLab deletes every non-victim user and restores the pristine victim', async (t) => {
  try {
    await mongoose.connect(TEST_MONGO_URL, { serverSelectionTimeoutMS: 1500 })
  } catch (error) {
    t.skip(`MongoDB not reachable at ${TEST_MONGO_URL}: ${error.message}`)
    return
  }

  try {
    await mongoose.connection.dropDatabase()

    // A "day two" database: the victim has been taken over and two attacker
    // accounts hold usernames they will later want to register again.
    const compromisedVictim = await User.create({
      username: 'victim',
      email: VICTIM.email,
      password: await bcrypt.hash('attacker-chosen-password', 4),
      firstName: VICTIM.first,
      lastName: VICTIM.last,
      address: 'attacker-controlled address',
    })
    const alice = await User.create(userDoc('alice'))
    const bob = await User.create(userDoc('bob'))

    await Cart.create({ user: alice._id, items: [] })
    const product = await Product.create({
      slug: 'reset-test-product',
      name: 'Reset Test Product',
      brand: 'ElectroMart',
      model: 'TEST-1',
      category: 'test',
      categoryLabel: 'Test',
      price: 100,
      stock: 1,
      description: 'A product that should be re-seeded.',
      specs: [],
      image: '/images/reset-test.png',
    })
    await Review.create({
      productSlug: product.slug,
      author: 'bob',
      rating: 1,
      comment: 'attacker review',
      userName: 'bob',
      isAuthor: true,
    })
    await mongoose.connection.db.collection('sessions').insertOne({ session: 'stale-session' })

    const summary = await resetLab()

    // Only the victim remains. Crucially, the victim row was preserved (same
    // _id), not deleted and re-created.
    const users = await User.find().lean()
    assert.equal(users.length, 1)
    assert.equal(users[0].username, 'victim')
    assert.equal(users[0].email, VICTIM.email.toLowerCase())
    assert.equal(String(users[0]._id), String(compromisedVictim._id), 'victim row should be kept')

    // ...and it is back to the documented credentials/flag.
    const restored = await User.findOne({ email: VICTIM.email }).select('+password')
    assert.equal(restored.firstName, VICTIM.first)
    assert.equal(restored.lastName, VICTIM.last.trim())
    assert.equal(restored.address, VICTIM.flag)
    assert.equal(await restored.comparePassword(VICTIM.password), true)
    assert.equal(await restored.comparePassword('attacker-chosen-password'), false)

    // Attacker usernames are free again.
    assert.equal(await User.countDocuments({ username: { $in: ['alice', 'bob'] } }), 0)
    assert.equal(summary.users, 2)
    assert.equal(summary.victim, 'victim')

    // Everything else lab-mutable is gone; seed() will rebuild products/reviews.
    assert.equal(await Cart.countDocuments(), 0)
    assert.equal(await Review.countDocuments(), 0)
    assert.equal(await Product.countDocuments(), 0)
    assert.equal(await mongoose.connection.db.collection('sessions').countDocuments(), 0)
  } finally {
    await mongoose.connection.dropDatabase().catch(() => {})
    await mongoose.disconnect().catch(() => {})
  }
})
