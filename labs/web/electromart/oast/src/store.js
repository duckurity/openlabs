'use strict'

const crypto = require('crypto')

/**
 * Callback identifiers are short, URL-safe, and unguessable enough for a lab.
 * They are not authentication tokens and must never be treated as credentials.
 */
const CALLBACK_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{7,63}$/

function newCallbackId() {
  return crypto.randomBytes(16).toString('hex')
}

function isValidCallbackId(value) {
  return typeof value === 'string' && CALLBACK_ID_RE.test(value)
}

/** Keep only the path (no query string) and cap it for safe display/logging. */
function safeEndpoint(value) {
  const raw = String(value === undefined || value === null ? '' : value)
  const withoutQuery = raw.split('?')[0].split('#')[0]
  return withoutQuery.slice(0, 512)
}

function safeMethod(value) {
  const method = String(value === undefined || value === null ? '' : value).trim().toUpperCase()
  return /^[A-Z]{1,16}$/.test(method) ? method : 'UNKNOWN'
}

function safeAddress(value) {
  const raw = String(value === undefined || value === null ? '' : value).trim()
  // Normalise IPv4-mapped IPv6 (::ffff:172.18.0.5) for readable dashboard rows.
  const normalised = raw.startsWith('::ffff:') ? raw.slice(7) : raw
  return normalised.slice(0, 64) || 'unknown'
}

function safeText(value, max = 2048) {
  return String(value === undefined || value === null ? '' : value).slice(0, max)
}

function safePort(value) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 && parsed <= 65_535 ? parsed : null
}

function safeHeaders(value) {
  const headers = Object.create(null)
  if (!value || typeof value !== 'object') return headers
  for (const [name, headerValue] of Object.entries(value)) {
    const key = safeText(name, 256).toLowerCase()
    if (!key) continue
    if (Array.isArray(headerValue)) {
      headers[key] = headerValue.map((entry) => safeText(entry, 16 * 1024))
    } else if (headerValue !== undefined && headerValue !== null) {
      headers[key] = safeText(headerValue, 16 * 1024)
    }
  }
  return headers
}

function safeRawHeaders(value) {
  if (!Array.isArray(value)) return []
  return value.slice(0, 512).map((entry) => safeText(entry, 16 * 1024))
}

function safeBody(value) {
  if (value === undefined || value === null) {
    return { body: '', bodyEncoding: 'utf8', bodyBytes: 0 }
  }
  const buffer = Buffer.isBuffer(value) ? value : Buffer.from(String(value), 'utf8')
  if (buffer.length === 0) {
    return { body: '', bodyEncoding: 'utf8', bodyBytes: 0 }
  }
  try {
    const body = new TextDecoder('utf-8', { fatal: true }).decode(buffer)
    return { body, bodyEncoding: 'utf8', bodyBytes: buffer.length }
  } catch (_error) {
    // Preserve non-UTF-8 request bytes exactly; the dashboard labels the encoding.
    return { body: buffer.toString('base64'), bodyEncoding: 'base64', bodyBytes: buffer.length }
  }
}

/**
 * Bounded in-memory interaction store.
 *
 * The OAST lab intentionally keeps request details (query string, headers, and
 * body) so the dashboard can show exactly what a callback received. Treat this
 * data as sensitive: it may contain cookies or authorization headers. The
 * service is loopback/internal-only and the UI warns operators accordingly.
 */
class InteractionStore {
  constructor({ max = 1000 } = {}) {
    this.max = Math.max(1, Number(max) || 1000)
    this.items = []
    this.counts = new Map()
    this.totalRecorded = 0
    this.totalRejected = 0
    this.nextInteractionId = 1
  }

  /**
   * @param {{callbackId:string, method:string, endpoint:string,
   *          sourceAddress:string, validation:string, url:string,
   *          headers:object, rawHeaders:string[], body:Buffer,
   *          protocol:string, httpVersion:string, remotePort:number}} input
   */
  record(input) {
    const method = safeMethod(input.method)
    const url = safeText(input.url, 2048)
    const headers = safeHeaders(input.headers)
    const queryIndex = url.indexOf('?')
    const query = queryIndex === -1 ? '' : url.slice(queryIndex)
    const body = safeBody(input.body)
    const item = Object.freeze({
      id: this.nextInteractionId++,
      timestamp: new Date().toISOString(),
      callbackId: String(input.callbackId),
      method,
      endpoint: safeEndpoint(input.endpoint),
      sourceAddress: safeAddress(input.sourceAddress),
      sourcePort: safePort(input.remotePort),
      validation: String(input.validation || 'accepted').slice(0, 64),
      protocol: safeText(input.protocol, 16),
      httpVersion: safeText(input.httpVersion, 16),
      host: safeText(headers.host, 255),
      url,
      query,
      requestLine: `${method} ${url} HTTP/${safeText(input.httpVersion, 16)}`,
      contentType: safeText(headers['content-type'], 255),
      headers,
      rawHeaders: safeRawHeaders(input.rawHeaders),
      body: body.body,
      bodyEncoding: body.bodyEncoding,
      bodyBytes: body.bodyBytes,
    })

    this.items.push(item)
    this.counts.set(item.callbackId, (this.counts.get(item.callbackId) || 0) + 1)
    this.totalRecorded += 1
    if (this.items.length > this.max) {
      this.items.splice(0, this.items.length - this.max)
    }
    return item
  }

  noteRejected() {
    this.totalRejected += 1
  }

  /** Newest first, optionally filtered by callback identifier. */
  list({ callbackId = null, limit = 100 } = {}) {
    const safeLimit = Math.max(1, Math.min(Number(limit) || 100, 1000))
    const filtered = callbackId
      ? this.items.filter((item) => item.callbackId === callbackId)
      : this.items
    return filtered.slice(-safeLimit).reverse()
  }

  /** Number of recorded (not merely retained) interactions for an identifier. */
  countFor(callbackId) {
    if (!callbackId) return this.totalRecorded
    return this.counts.get(callbackId) || 0
  }

  stats() {
    const unique = new Set(this.items.map((item) => item.callbackId))
    return {
      totalRecorded: this.totalRecorded,
      totalRejected: this.totalRejected,
      retained: this.items.length,
      capacity: this.max,
      uniqueCallbackIds: unique.size,
    }
  }
}

module.exports = {
  InteractionStore,
  CALLBACK_ID_RE,
  newCallbackId,
  isValidCallbackId,
  safeEndpoint,
  safeMethod,
  safeAddress,
}
