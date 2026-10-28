'use strict'

/** 404 and error-handling middleware (registered last in the app). */

function notFound(req, res) {
  res.status(404).render('error', {
    code: 404,
    message: "The page you're looking for doesn't exist or isn't available in this phase of ElectroMart.",
  })
}

// eslint-disable-next-line no-unused-vars
function errorHandler(error, req, res, next) {
  if (res.headersSent) return next(error)

  console.error(`[http] ${req.method} ${req.originalUrl} →`, (error && error.stack) || error)

  const status = Number(error && error.status) || 500
  const hideDetails = status >= 500 && (process.env.NODE_ENV === 'production' || !process.env.NODE_ENV)
  const message = hideDetails
    ? 'Something went wrong on our side. Please try again.'
    : (error && error.message) || 'Request failed.'

  res.status(status).render('error', { code: status, message })
}

module.exports = { notFound, errorHandler }
