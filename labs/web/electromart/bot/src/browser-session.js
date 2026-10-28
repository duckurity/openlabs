'use strict'

const { chromium } = require('playwright')

const { ShutdownError } = require('./errors')
const { throwIfAborted } = require('./util')

/**
 * Create a clean browser, context and page for one cycle. The returned session
 * owns an idempotent close() so the cycle's finally block and the shutdown
 * handler can both call it safely.
 */
async function createBrowserSession({ config, logger, cycleId, signal }) {
  throwIfAborted(signal)
  logger.debug('browser.starting', { cycleId, headless: config.headless })

  const browser = await chromium.launch({
    headless: config.headless,
    timeout: config.timeoutMs,
    // Docker's default /dev/shm is often too small for Chromium.
    args: ['--disable-dev-shm-usage'],
  })

  let context = null
  try {
    throwIfAborted(signal)
    context = await browser.newContext({
      viewport: { width: 1366, height: 900 },
      locale: 'en-GB',
      acceptDownloads: false,
    })
    context.setDefaultTimeout(config.timeoutMs)
    context.setDefaultNavigationTimeout(config.timeoutMs)

    const page = await context.newPage()

    let closePromise = null
    const session = {
      browser,
      context,
      page,
      close() {
        if (!closePromise) {
          closePromise = (async () => {
            try {
              await context.close()
            } catch (error) {
              logger.warn('browser.context-close-failed', {
                cycleId,
                error: logger.sanitize(error && error.message ? error.message : error),
              })
            }
            try {
              await browser.close()
            } catch (error) {
              logger.warn('browser.close-failed', {
                cycleId,
                error: logger.sanitize(error && error.message ? error.message : error),
              })
            }
            logger.info('browser.closed', { cycleId })
          })()
        }
        return closePromise
      },
    }

    logger.info('browser.started', {
      cycleId,
      browserVersion: browser.version(),
      headless: config.headless,
    })
    return session
  } catch (error) {
    try {
      if (context) await context.close()
    } catch (_closeError) {
      // The original error is the useful one.
    }
    try {
      await browser.close()
    } catch (_closeError) {
      // Ignore secondary close failures.
    }
    throw error
  }
}

module.exports = { createBrowserSession }
