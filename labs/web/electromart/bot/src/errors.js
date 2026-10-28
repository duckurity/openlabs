'use strict'

/** Base class for failures that are already classified for logging/retries. */
class BotError extends Error {
  constructor({ message, category = 'workflow', step = null, transient = true, cause = null }) {
    super(message)
    this.name = this.constructor.name
    this.category = category
    this.step = step
    this.transient = transient
    if (cause) this.cause = cause
  }
}

/** Shutdown was requested while a step was running or waiting. */
class ShutdownError extends BotError {
  constructor(message = 'shutdown requested') {
    super({ message, category: 'shutdown', transient: false })
  }
}

/** The application never became ready within the bounded readiness window. */
class AppNotReadyError extends BotError {
  constructor(message, cause = null) {
    super({ message, category: 'readiness', step: 'readiness', transient: true, cause })
  }
}

/** The login form rejected the configured victim credentials. */
class AuthenticationError extends BotError {
  constructor(message, cause = null) {
    super({ message, category: 'auth', step: 'authenticate', transient: false, cause })
  }
}

/** A safe wrapper for a failed step. */
class WorkflowError extends BotError {
  constructor({ message, category = 'workflow', step = null, transient = true, cause = null }) {
    super({ message, category, step, transient, cause })
  }
}

module.exports = {
  BotError,
  ShutdownError,
  AppNotReadyError,
  AuthenticationError,
  WorkflowError,
}
