'use strict'

const { loadConfig } = require('./config')
const { createLogger, makeSanitizer, safeError } = require('./logger')
const { runVictimCycle } = require('./workflow')
const { runOastXssValidation } = require('./xss-check')
const { ShutdownError } = require('./errors')
const { sleep } = require('./util')

function playwrightVersion() {
  try {
    return require('playwright/package.json').version
  } catch (_error) {
    return 'unknown'
  }
}

async function main() {
  const { config, warnings } = loadConfig()
  const logger = createLogger({
    level: config.logLevel,
    // Defence in depth: even an unexpected error string cannot print the
    // configured victim password (the flag and cookies are also redacted).
    secrets: [config.victim.password],
  })

  for (const warning of warnings) logger.warn('config.warning', { warning })

  logger.info('bot.start', {
    baseUrl: config.baseUrl,
    readyPath: config.readyPath,
    cycleIntervalMs: config.cycleIntervalMs,
    timeoutMs: config.timeoutMs,
    maxRetries: config.maxRetries,
    readyTimeoutMs: config.readyTimeoutMs,
    headless: config.headless,
    screenshotsOnFailure: config.screenshotsOnFailure,
    productPathCount: config.productPaths.length,
    productPathMode: config.productPaths.length > 0 ? 'explicit' : 'catalog-discovery',
    commentLinksEnabled: config.commentLinksEnabled,
    allowedLinkOrigins: config.allowedLinkOrigins,
    oastBaseUrl: config.oastBaseUrl,
    xssCheckEnabled: config.xssCheckEnabled,
    maxCycles: config.maxCycles || null,
    account: 'configured-victim',
    passwordSource: process.env.VICTIM_PASSWORD ? 'environment' : 'lab-default',
    playwrightVersion: playwrightVersion(),
    nodeVersion: process.version,
    pid: process.pid,
  })

  const controller = new AbortController()
  let shuttingDown = false
  let shutdownReason = null
  let requestedExitCode = 0
  let activeSession = null
  let cycleRunning = false
  let cycleNumber = 0
  let completedCycles = 0
  let finished = false
  let forceTimer = null

  const onResources = (session) => {
    activeSession = session
  }

  const closeActive = async () => {
    const session = activeSession
    if (!session) return
    await session.close()
    if (activeSession === session) activeSession = null
  }

  const finish = async (reason, exitCode) => {
    if (finished) return
    finished = true
    if (forceTimer) clearTimeout(forceTimer)

    await closeActive()
    logger.info('bot.stop', {
      reason,
      cyclesAttempted: cycleNumber,
      cyclesCompleted: completedCycles,
      exitCode,
    })

    // Give stdout a moment to flush before leaving the container.
    await new Promise((resolve) => setTimeout(resolve, 50))
    process.exit(exitCode)
  }

  const requestShutdown = (reason, exitCode = 0) => {
    if (shuttingDown) return
    shuttingDown = true
    shutdownReason = reason
    requestedExitCode = exitCode

    logger.warn('shutdown.begin', {
      reason,
      exitCode,
      cycle: cycleNumber,
      cycleRunning,
    })

    // Wake readiness polling / inter-cycle waits; close the active browser so
    // any in-flight Playwright call fails promptly and the loop can unwind.
    controller.abort()
    closeActive().then(
      () => logger.info('shutdown.cleanup-complete', { reason }),
      (error) =>
        logger.warn('shutdown.cleanup-failed', {
          reason,
          error: safeError(error, logger.sanitize),
        })
    )

    // Last-resort guard. Docker's stop_grace_period is slightly longer.
    forceTimer = setTimeout(() => {
      logger.error('shutdown.forced', { reason, timeoutMs: config.shutdownTimeoutMs })
      process.exit(exitCode === 0 ? 1 : exitCode)
    }, config.shutdownTimeoutMs + 3_000)
    forceTimer.unref()
  }

  process.on('SIGTERM', () => requestShutdown('SIGTERM'))
  process.on('SIGINT', () => requestShutdown('SIGINT'))
  process.on('uncaughtException', (error) => {
    logger.error('bot.uncaught-exception', { error: safeError(error, logger.sanitize) })
    requestShutdown('uncaughtException', 1)
  })
  process.on('unhandledRejection', (reason) => {
    logger.error('bot.unhandled-rejection', {
      error: logger.sanitize(reason && reason.message ? reason.message : reason),
    })
    requestShutdown('unhandledRejection', 1)
  })

  logger.info('bot.loop-ready', {
    intervalMs: config.cycleIntervalMs,
    maxCycles: config.maxCycles || null,
  })

  // One explicit, isolated XSS/OAST validation per bot process. It runs in its
  // own fresh browser context with synthetic values, before the normal victim
  // browsing loop starts, and never touches the victim account or flag.
  if (config.xssCheckEnabled) {
    const validationCycleId = `startup-${Date.now().toString(36)}`
    try {
      await runOastXssValidation({
        config,
        logger,
        signal: controller.signal,
        cycleId: validationCycleId,
      })
    } catch (error) {
      if (error instanceof ShutdownError || shuttingDown) {
        logger.info('xss.validation.interrupted', {
          cycleId: validationCycleId,
          step: error.step || 'unknown',
        })
      } else {
        logger.error('xss.validation.failed', {
          cycleId: validationCycleId,
          step: error.step || 'xss-validation',
          category: error.category || 'xss',
          error: safeError(error, logger.sanitize),
        })
      }
    }
  } else {
    logger.info('xss.validation.disabled', {})
  }

  try {
    while (!shuttingDown) {
      if (config.maxCycles > 0 && cycleNumber >= config.maxCycles) {
        logger.info('bot.test-bound-reached', {
          cyclesAttempted: cycleNumber,
          cyclesCompleted: completedCycles,
        })
        break
      }

      cycleNumber += 1
      const cycleId = `${String(cycleNumber).padStart(4, '0')}-${Date.now().toString(36)}`
      const startedAt = Date.now()

      // Invariant: a new cycle can never overlap the previous one because the
      // loop awaits runVictimCycle() before continuing. This guard would catch
      // a future regression that breaks that sequencing.
      if (cycleRunning) {
        logger.error('cycle.overlap-detected', { cycle: cycleNumber, cycleId })
        requestShutdown('cycle-overlap', 1)
        break
      }
      cycleRunning = true

      logger.info('cycle.begin', {
        cycle: cycleNumber,
        cycleId,
        intervalMs: config.cycleIntervalMs,
      })

      try {
        const result = await runVictimCycle({
          config,
          logger,
          signal: controller.signal,
          cycleId,
          cycleNumber,
          onResources,
        })
        completedCycles += 1
        logger.info('cycle.complete', {
          cycle: cycleNumber,
          cycleId,
          durationMs: result.durationMs,
          productsVisited: result.productsVisited,
          returnedHome: result.returnedHome,
          loggedOut: result.loggedOut,
          commentLink: result.commentLink && result.commentLink.followed
            ? 'followed'
            : (result.commentLink && result.commentLink.reason) || 'none',
          loginReplay: result.loginReplay ? result.loginReplay.outcome : 'skipped',
        })
      } catch (error) {
        if (error instanceof ShutdownError || shuttingDown) {
          logger.info('cycle.interrupted', {
            cycle: cycleNumber,
            cycleId,
            step: error.step || 'unknown',
          })
        } else {
          logger.error('cycle.failed', {
            cycle: cycleNumber,
            cycleId,
            durationMs: Date.now() - startedAt,
            step: error.step || 'unknown',
            category: error.category || 'workflow',
            error: safeError(error, logger.sanitize),
          })
        }
      } finally {
        cycleRunning = false
      }

      // Always clean up before scheduling the next cycle, even after a failure
      // that happened after the browser session was created.
      await closeActive()

      if (shuttingDown) break
      if (config.maxCycles > 0 && cycleNumber >= config.maxCycles) {
        logger.info('bot.test-bound-reached', {
          cyclesAttempted: cycleNumber,
          cyclesCompleted: completedCycles,
        })
        break
      }

      logger.info('cycle.wait', {
        cycle: cycleNumber,
        cycleId,
        intervalMs: config.cycleIntervalMs,
      })
      const slept = await sleep(config.cycleIntervalMs, controller.signal)
      if (!slept) break
    }
  } catch (error) {
    logger.error('bot.fatal', { error: safeError(error, logger.sanitize) })
    requestShutdown('fatal', 1)
  }

  const reason = shuttingDown
    ? shutdownReason || 'shutdown'
    : config.maxCycles > 0
      ? 'max-cycles'
      : 'loop-ended'
  await finish(reason, shuttingDown ? requestedExitCode : 0)
}

main().catch((error) => {
  // Configuration failures happen before the logger exists. Keep the report
  // clear and safe: no environment dump and no credential values.
  const sanitize = makeSanitizer([process.env.VICTIM_PASSWORD])
  const report = {
    ts: new Date().toISOString(),
    level: 'error',
    service: 'victim-bot',
    event: 'bot.config-error',
    error: {
      name: error && error.name ? error.name : 'Error',
      message: sanitize(error && error.message ? error.message : error),
    },
  }
  console.error(JSON.stringify(report))
  process.exit(1)
})
