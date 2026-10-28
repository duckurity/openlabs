'use strict'

const config = require('./config')
const { connectWithRetry, mongoose } = require('./db')
const { createApp, FALLBACK_SECRET } = require('./app')

async function main() {
  if (!config.session.secret) {
    console.warn('[security] WARNING: SESSION_SECRET is not set. Using an insecure fallback — set SESSION_SECRET in .env!')
  }
  if (config.session.secure) {
    console.warn('[security] NOTE: secure cookies enabled — serve over HTTPS when SESSION_SECURE=true.')
  }

  // Only start accepting traffic once the database is reachable.
  await connectWithRetry()

  // Lab reset: this is an account-takeover lab, so every boot restores the
  // INITIAL "day one" state — wiping any extra accounts an attacker registered
  // (so re-registering a username never fails with "already taken"), attacker
  // carts/reviews, stale sessions, AND any completed takeover of the victim.
  // resetLab() clears the mutable/user data; seed() (below) then rebuilds the
  // 20 products + source reviews and recreates the pristine victim.
  if (config.resetOnBoot) {
    const { resetLab } = require('./reset')
    await resetLab()
  }

  // Idempotent seed: ensures the 20 products exist in MongoDB on every startup.
  const { seed } = require('./seed')
  await seed()

  const app = createApp()
  const server = app.listen(config.port, () => {
    console.log(`ElectroMart is running at http://localhost:${config.port} (env: ${config.env})`)
  })

  const shutdown = (signal) => {
    console.log(`[server] ${signal} received — shutting down gracefully…`)
    server.close(() => {
      mongoose.connection
        .close()
        .catch(() => {})
        .finally(() => process.exit(0))
    })
    // Hard exit if sockets refuse to drain.
    setTimeout(() => process.exit(1), 10000).unref()
  }

  process.on('SIGTERM', () => shutdown('SIGTERM'))
  process.on('SIGINT', () => shutdown('SIGINT'))
  process.on('unhandledRejection', (reason) => {
    console.error('[server] unhandled rejection:', reason)
  })

  server.on('error', (error) => {
    console.error('[server] failed to start:', error)
    process.exit(1)
  })
}

main().catch((error) => {
  console.error('[server] fatal startup error:', error)
  process.exit(1)
})
