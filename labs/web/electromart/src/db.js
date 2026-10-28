'use strict'

const mongoose = require('mongoose')
const config = require('./config')

mongoose.set('strictQuery', true)

const MAX_ATTEMPTS = 10
const RETRY_DELAY_MS = 1500

/**
 * Connect to MongoDB with bounded retries so the app boots gracefully
 * even when the database container is still starting up.
 */
async function connectWithRetry() {
  let lastError
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      await mongoose.connect(config.mongoUrl, { serverSelectionTimeoutMS: 5000 })
      console.log(`[db] connected to MongoDB at ${config.mongoUrl}`)
      return
    } catch (error) {
      lastError = error
      if (attempt === MAX_ATTEMPTS) break
      console.warn(
        `[db] connection attempt ${attempt}/${MAX_ATTEMPTS} failed (${error.message}) — retrying in ${RETRY_DELAY_MS / 1000}s…`
      )
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS))
    }
  }
  throw lastError
}

mongoose.connection.on('disconnected', () => console.warn('[db] disconnected from MongoDB'))
mongoose.connection.on('reconnected', () => console.log('[db] reconnected to MongoDB'))
mongoose.connection.on('error', (error) => console.error('[db] MongoDB error:', error.message))

module.exports = { connectWithRetry, mongoose }
