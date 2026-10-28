'use strict'

const { AppNotReadyError, ShutdownError } = require('./errors')
const { sleep, throwIfAborted } = require('./util')

const READINESS_LOG_INTERVAL_MS = 15_000

function healthUrl(baseUrl, readyPath) {
  const suffix = String(readyPath).startsWith('/')
    ? String(readyPath)
    : `/${readyPath}`
  return `${baseUrl}${suffix}`
}

async function fetchWithTimeout(url, timeoutMs, signal) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const forwardAbort = () => controller.abort()
  if (signal) signal.addEventListener('abort', forwardAbort, { once: true })

  try {
    return await fetch(url, {
      method: 'GET',
      redirect: 'follow',
      headers: { accept: 'application/json' },
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', forwardAbort)
  }
}

/**
 * Bounded readiness polling for one lab service. One request per readyPollMs,
 * warnings throttled to one every 15 seconds. The optional expectedService
 * check proves we reached the intended service, not merely any 2xx endpoint.
 */
async function waitForService({
  baseUrl,
  readyPath,
  label,
  expectedService = null,
  config,
  logger,
  signal,
  cycleId,
}) {
  const url = healthUrl(baseUrl, readyPath)
  const startedAt = Date.now()
  const deadline = startedAt + config.readyTimeoutMs
  let attempts = 0
  let lastLogAt = 0
  let lastStatus = null

  logger.debug(`${label}.readiness-start`, {
    cycleId,
    url,
    timeoutMs: config.readyTimeoutMs,
    pollMs: config.readyPollMs,
  })

  while (true) {
    throwIfAborted(signal)
    attempts += 1

    try {
      const response = await fetchWithTimeout(
        url,
        Math.min(config.timeoutMs, 10_000),
        signal
      )
      lastStatus = response.status
      if (response.ok) {
        let payload = null
        try {
          payload = await response.json()
        } catch (_error) {
          payload = null
        }
        const serviceMatches = !expectedService ||
          !payload ||
          payload.service === undefined ||
          payload.service === expectedService
        if (serviceMatches && (!payload || payload.status === undefined || payload.status === 'ok')) {
          const waitedMs = Date.now() - startedAt
          if (attempts > 1) {
            logger.info(`${label}.ready`, { cycleId, attempts, waitedMs, status: response.status })
          } else {
            logger.debug(`${label}.ready`, { cycleId, attempts, waitedMs, status: response.status })
          }
          return { attempts, waitedMs }
        }
        lastStatus = payload && payload.service
          ? `unexpected-service:${payload.service}`
          : 'unexpected-payload'
      }
    } catch (error) {
      if (signal && signal.aborted) throw new ShutdownError()
      lastStatus = error && error.name ? error.name : 'request-failed'
    }

    const now = Date.now()
    if (now >= deadline) {
      throw new AppNotReadyError(
        `${label} service not ready after ${config.readyTimeoutMs}ms (${attempts} attempt(s), last status: ${lastStatus})`
      )
    }
    if (attempts === 1 || now - lastLogAt >= READINESS_LOG_INTERVAL_MS) {
      lastLogAt = now
      logger.warn(`${label}.not-ready`, {
        cycleId,
        attempt: attempts,
        lastStatus,
        retryInMs: config.readyPollMs,
        waitedMs: now - startedAt,
      })
    }

    const completed = await sleep(
      Math.min(config.readyPollMs, Math.max(0, deadline - now)),
      signal
    )
    if (!completed) throw new ShutdownError()
  }
}

function waitForApp({ config, logger, signal, cycleId }) {
  return waitForService({
    baseUrl: config.baseUrl,
    readyPath: config.readyPath,
    label: 'app',
    expectedService: null,
    config,
    logger,
    signal,
    cycleId,
  })
}

function waitForOast({ config, logger, signal, cycleId }) {
  return waitForService({
    baseUrl: config.oastBaseUrl,
    readyPath: config.oastReadyPath,
    label: 'oast',
    expectedService: 'oast',
    config,
    logger,
    signal,
    cycleId,
  })
}

module.exports = { waitForApp, waitForOast, healthUrl }
