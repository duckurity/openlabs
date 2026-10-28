'use strict'

const bcrypt = require('bcryptjs')
const config = require('./config')
const User = require('./models/user')

/**
 * ============================================================
 *  Phase 1.3 — the dedicated lab VICTIM account
 * ============================================================
 *
 * A predictable, documented victim account is created automatically on every
 * boot by the idempotent seed (see seed.js → seedVictim()).  It exists after a
 * fresh Docker setup and survives container restarts without being duplicated
 * (guarded by the unique `username` / `email` indexes and an upsert check).
 *
 * The lab flag lives in the victim's **Delivery address** field — stored as the
 * real `address` column value in MongoDB, never hard-coded in a template.  The
 * flag is only ever shown on the victim's own /profile page.
 */

// Exact lab credentials (documented in the README).
const VICTIM = {
  first: 'victim',
  last: ' account', // literal trailing space required by the spec ("victim account")
  email: 'victimEmail@gmail.com',
  password: 'Victim#XSStoAccountTackOver#2',
  // The lab flag — the protected target of the exercise.
  flag: 'duck{XSS_to_AccountTakeOver}',
}

// A safe, natural username. The account is looked up and guarded by its unique
// email first, so a clean lab always creates it and restarts never duplicate it.
const VICTIM_USERNAME = 'victim'

/** The canonical, documented content of the victim account. */
function victimFields(passwordHash) {
  return {
    username: VICTIM_USERNAME,
    email: VICTIM.email,
    password: passwordHash,
    firstName: VICTIM.first,
    lastName: VICTIM.last,
    address: VICTIM.flag, // the flag is stored in Delivery address
  }
}

/**
 * Idempotently create (or verify) the victim account.
 * @returns {Promise<{exists: boolean, created: boolean, username: string|null}>}
 */
async function seedVictim() {
  // Primary identity is the unique email — stable across runs.
  const existing = await User.findOne({ email: VICTIM.email }).exec()
  if (existing) {
    return { exists: true, created: false, username: existing.username }
  }

  const passwordHash = await bcrypt.hash(VICTIM.password, config.bcryptRounds)

  try {
    const user = await User.create(victimFields(passwordHash))
    return { exists: true, created: true, username: user.username }
  } catch (error) {
    if (error && error.code === 11000) {
      // A concurrent insert or a pre-taken username/email. Never overwrite.
      const again = await User.findOne({ email: VICTIM.email }).exec()
      if (again) return { exists: true, created: false, username: again.username }
      console.warn('[seed] could not create victim (username/email taken by a different account) — skipping.')
      return { exists: false, created: false, username: null }
    }
    throw error
  }
}

/**
 * Restore the victim account IN PLACE to its documented "day one" state.
 *
 * Unlike seedVictim(), this never skips an existing victim: it rewrites the
 * canonical username/email/password/name/address (flag), so a completed
 * account takeover is undone while the victim row itself is kept (resetLab
 * only deletes accounts that are not the victim). Matched by the unique email
 * and upserted, so it also creates the victim on a completely fresh database.
 *
 * @returns {Promise<{exists: boolean, username: string|null}>}
 */
async function restoreVictim() {
  const passwordHash = await bcrypt.hash(VICTIM.password, config.bcryptRounds)

  try {
    const victim = await User.findOneAndUpdate(
      { email: VICTIM.email },
      { $set: victimFields(passwordHash) },
      { new: true, upsert: true, runValidators: true, setDefaultsOnInsert: true }
    ).exec()
    return { exists: true, username: victim.username }
  } catch (error) {
    if (error && error.code === 11000) {
      // A different account still holds the `victim` username (resetLab
      // removes those first, so this is only a safety net for direct calls).
      const existing = await User.findOne({ email: VICTIM.email }).exec()
      if (existing) return { exists: true, username: existing.username }
      console.warn('[reset] could not restore victim (username already held by another account).')
      return { exists: false, username: null }
    }
    throw error
  }
}

module.exports = { seedVictim, restoreVictim, VICTIM, VICTIM_USERNAME }
