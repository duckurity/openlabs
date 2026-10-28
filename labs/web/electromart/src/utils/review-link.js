'use strict'

/**
 * Safe, display-only link rendering for customer reviews.
 *
 * This is deliberately NOT an HTML passthrough. The comment text is escaped
 * first, then only two kinds of token become an anchor:
 *
 *   - an absolute http(s) URL, matching the actual web schemes; and
 *   - a site-relative path beginning with `/` (but not protocol-relative `//`).
 *
 * A `javascript:`, `data:`, `mailto:`, `file:`, or other scheme therefore stays
 * inert text. The bot separately validates the destination origin before it
 * follows anything.
 */
const LINK_PATTERN = /(?:https?:\/\/[^\s<>"']+|\/(?:home|preferences=|product\/|login|register|cart|profile)(?:[^\s<>"']*)?)/gi

function escapeHtml(value) {
  return String(value === undefined || value === null ? '' : value).replace(
    /[&<>"']/g,
    (character) => {
      if (character === '&') return '&amp;'
      if (character === '<') return '&lt;'
      if (character === '>') return '&gt;'
      if (character === '"') return '&quot;'
      return '&#39;'
    }
  )
}

/**
 * Remove sentence punctuation that was adjacent to a URL, keeping it as text.
 * This avoids turning `see /home.` into a link whose href ends with a dot.
 */
function splitTrailingPunctuation(value) {
  let token = String(value)
  let trailing = ''

  const punctuation = token.match(/[.,;:!]+$/)
  if (punctuation) {
    trailing = punctuation[0]
    token = token.slice(0, -punctuation[0].length)
  }

  // Strip only *unmatched* closing brackets, so a URL that legitimately
  // contains a balanced pair is left alone.
  while (/[)\]}]$/.test(token)) {
    const last = token.slice(-1)
    const opener = last === ')' ? '(' : last === ']' ? '[' : '{'
    if (token.includes(opener)) break
    trailing = last + trailing
    token = token.slice(0, -1)
  }

  return { token, trailing }
}

function isSafeHref(token) {
  if (/^https?:\/\//i.test(token)) {
    try {
      const url = new URL(token)
      return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password
    } catch (_error) {
      return false
    }
  }
  return token.startsWith('/') && !token.startsWith('//')
}

/**
 * Convert a plain review comment into escaped HTML with safe anchors.
 *
 * @param {string} text
 * @returns {string}
 */
function renderReviewComment(text) {
  const raw = String(text === undefined || text === null ? '' : text)
  let output = ''
  let lastIndex = 0

  for (const match of raw.matchAll(LINK_PATTERN)) {
    const index = match.index
    const { token, trailing } = splitTrailingPunctuation(match[0])

    output += escapeHtml(raw.slice(lastIndex, index))
    if (token && isSafeHref(token)) {
      output +=
        `<a class="review-link" href="${escapeHtml(token)}" ` +
        `rel="nofollow noopener noreferrer">${escapeHtml(token)}</a>`
    } else {
      output += escapeHtml(token)
    }
    output += escapeHtml(trailing)
    lastIndex = index + match[0].length
  }

  output += escapeHtml(raw.slice(lastIndex))
  return output
}

module.exports = {
  renderReviewComment,
  splitTrailingPunctuation,
  isSafeHref,
}
