'use strict'

/**
 * Abortable delay. Resolves to true for a normal timeout and false when the
 * AbortSignal fired (used to leave the persistent loop promptly on shutdown).
 *
 * @param {number} ms
 * @param {AbortSignal} signal
 * @returns {Promise<boolean>}
 */
function sleep(ms, signal) {
  return new Promise((resolve) => {
    if (signal && signal.aborted) return resolve(false)

    let timer = null
    const finish = (completed) => {
      if (timer) clearTimeout(timer)
      if (signal) signal.removeEventListener('abort', onAbort)
      resolve(completed)
    }
    const onAbort = () => finish(false)

    timer = setTimeout(() => finish(true), Math.max(0, ms))
    if (signal) signal.addEventListener('abort', onAbort, { once: true })
  })
}

function throwIfAborted(signal) {
  if (signal && signal.aborted) {
    const { ShutdownError } = require('./errors')
    throw new ShutdownError()
  }
}

function shorten(value, max = 120) {
  const text = String(value === undefined || value === null ? '' : value)
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

module.exports = { sleep, throwIfAborted, shorten }
