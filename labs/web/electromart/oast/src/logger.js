'use strict'

const LEVELS = Object.freeze({ debug: 10, info: 20, warn: 30, error: 40 })

/**
 * Structured JSON logger. Request details are stored on interactions and shown
 * only by the dashboard/JSON API; this logger is deliberately metadata-only so
 * Docker logs do not become a second copy of cookies, headers, or bodies.
 */
function createLogger({ level = 'info' } = {}) {
  const threshold = LEVELS[level] === undefined ? LEVELS.info : LEVELS[level]

  function emit(levelName, event, meta = {}) {
    if (LEVELS[levelName] < threshold) return
    const entry = {
      ts: new Date().toISOString(),
      level: levelName,
      service: 'oast',
      event,
    }
    for (const [key, value] of Object.entries(meta || {})) {
      if (value !== undefined) entry[key] = value
    }
    // One JSON object per line keeps docker logs greppable.
    console.log(JSON.stringify(entry))
  }

  return {
    debug: (event, meta) => emit('debug', event, meta),
    info: (event, meta) => emit('info', event, meta),
    warn: (event, meta) => emit('warn', event, meta),
    error: (event, meta) => emit('error', event, meta),
  }
}

module.exports = { createLogger }
