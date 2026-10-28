'use strict'

const { loadConfig } = require('./config')
const { createLogger } = require('./logger')
const { createApp } = require('./app')

async function main() {
  const { config, warnings } = loadConfig()
  const logger = createLogger({ level: config.logLevel })

  for (const warning of warnings) logger.warn('config.warning', { warning })

  const { app, store } = createApp({ config, logger })
  const server = app.listen(config.port, config.host)

  // Bound slow clients. Values are also configurable for stricter labs.
  server.requestTimeout = config.requestTimeoutMs
  server.headersTimeout = Math.min(config.requestTimeoutMs, 10_000)
  server.keepAliveTimeout = Math.min(5_000, config.requestTimeoutMs)
  server.maxRequestsPerSocket = 1000

  server.on('listening', () => {
    logger.info('oast.start', {
      host: config.host,
      port: config.port,
      callbackOrigin: config.publicOrigin,
      maxInteractions: config.maxInteractions,
      maxBodyBytes: config.maxBodyBytes,
      requestTimeoutMs: config.requestTimeoutMs,
      logLevel: config.logLevel,
      pid: process.pid,
    })
  })

  server.on('error', (error) => {
    logger.error('oast.server-error', {
      name: error && error.name ? error.name : 'Error',
      code: error && error.code ? error.code : undefined,
    })
    process.exit(1)
  })

  let shuttingDown = false
  const shutdown = (signal) => {
    if (shuttingDown) return
    shuttingDown = true
    logger.info('oast.shutdown-begin', { signal, interactions: store.stats().totalRecorded })

    const force = setTimeout(() => {
      logger.error('oast.shutdown-forced', { signal, timeoutMs: config.shutdownTimeoutMs })
      process.exit(1)
    }, config.shutdownTimeoutMs + 1_000)
    force.unref()

    server.close((error) => {
      clearTimeout(force)
      if (error) {
        logger.error('oast.shutdown-error', { message: error.message })
        process.exit(1)
      }
      logger.info('oast.stop', { signal })
      process.exit(0)
    })

    // Stop accepting new sockets promptly; in-flight requests get the grace budget.
    server.closeIdleConnections?.()
  }

  process.on('SIGTERM', () => shutdown('SIGTERM'))
  process.on('SIGINT', () => shutdown('SIGINT'))
  process.on('uncaughtException', (error) => {
    logger.error('oast.uncaught-exception', {
      name: error && error.name ? error.name : 'Error',
      message: error && error.message ? error.message : 'unknown',
    })
    shutdown('uncaughtException')
  })
  process.on('unhandledRejection', (reason) => {
    logger.error('oast.unhandled-rejection', {
      message: reason && reason.message ? reason.message : String(reason),
    })
    shutdown('unhandledRejection')
  })
}

if (require.main === module) {
  main()
}

module.exports = { main }
