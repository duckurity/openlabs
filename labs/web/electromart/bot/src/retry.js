'use strict'

const { BotError, ShutdownError, WorkflowError } = require('./errors')
const { safeError } = require('./logger')
const { sleep, throwIfAborted } = require('./util')

function looksTransient(error) {
  const message = String((error && error.message) || error || '')
  return [
    'Timeout',
    'timeout',
    'net::ERR',
    'ECONNREFUSED',
    'ECONNRESET',
    'ENOTFOUND',
    'EAI_AGAIN',
    'socket hang up',
    'Target closed',
    'Target page, context or browser has been closed',
    'browser has been closed',
    'Execution context was destroyed',
    'Navigation failed',
  ].some((needle) => message.includes(needle))
}

function classifyError(error, step, fallbackCategory = 'workflow') {
  if (error instanceof BotError) return error
  const transient = looksTransient(error)
  return new WorkflowError({
    message: error && error.message ? error.message : String(error),
    category: transient ? 'transient' : fallbackCategory,
    step,
    transient,
    cause: error,
  })
}

/**
 * Bounded retry helper for transient browser/navigation operations. The
 * number of HTTP attempts is maxRetries + 1. Each retry waits with exponential
 * backoff capped at 10s, so a failure cannot create a tight retry storm.
 */
async function retryOperation({
  config,
  logger,
  signal,
  cycleId,
  step,
  run,
  isRetryable = (error) => error.transient !== false,
  category = 'workflow',
}) {
  const maxAttempts = config.maxRetries + 1

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    throwIfAborted(signal)
    try {
      return await run(attempt)
    } catch (error) {
      if (error instanceof ShutdownError) throw error
      const classified = classifyError(error, step, category)
      if (!classified.step) classified.step = step
      if (attempt >= maxAttempts || !isRetryable(classified)) throw classified

      const delayMs = Math.min(
        config.retryBaseDelayMs * 2 ** (attempt - 1),
        10_000
      )
      logger.warn('retry', {
        cycleId,
        step,
        attempt,
        maxAttempts,
        delayMs,
        category: classified.category,
        error: safeError(classified, logger.sanitize),
      })

      const completed = await sleep(delayMs, signal)
      if (!completed) throw new ShutdownError()
    }
  }

  // Unreachable: the loop either returns or throws.
  throw new WorkflowError({
    message: `retry operation "${step}" exhausted without a result`,
    step,
    category,
  })
}

module.exports = { retryOperation, classifyError, looksTransient }
