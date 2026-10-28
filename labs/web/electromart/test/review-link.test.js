'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')

const { renderReviewComment, splitTrailingPunctuation, isSafeHref } = require('../src/utils/review-link')

test('review link rendering escapes all comment text', () => {
  const html = renderReviewComment('<script>alert(1)</script> & "quotes"')
  assert.equal(
    html,
    '&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;quotes&quot;'
  )
  assert.doesNotMatch(html, /<script>/)
})

test('review link rendering creates anchors for absolute http(s) links', () => {
  const html = renderReviewComment('See https://example.com/deal?a=1&b=2 for details.')
  assert.equal(
    html,
    'See <a class="review-link" href="https://example.com/deal?a=1&amp;b=2" rel="nofollow noopener noreferrer">https://example.com/deal?a=1&amp;b=2</a> for details.'
  )
})

test('review link rendering creates anchors for site-relative lab routes', () => {
  const html = renderReviewComment('Try /home?preferences=phone or /preferences=tv now.')
  assert.equal(
    html,
    'Try <a class="review-link" href="/home?preferences=phone" rel="nofollow noopener noreferrer">/home?preferences=phone</a> or <a class="review-link" href="/preferences=tv" rel="nofollow noopener noreferrer">/preferences=tv</a> now.'
  )
})

test('review link rendering leaves unsupported schemes inert', () => {
  for (const text of ['javascript:alert(1)', 'data:text/html,<b>x</b>', 'mailto:test@example.com', '//evil.test/x']) {
    const html = renderReviewComment(text)
    assert.doesNotMatch(html, /<a /, text)
    assert.doesNotMatch(html, /href=/, text)
  }
})

test('review link rendering keeps trailing sentence punctuation outside the anchor', () => {
  const html = renderReviewComment('See /home?preferences=phone, then /product/ifilter-cold).')
  assert.match(html, />\/home\?preferences=phone<\/a>,/)
  assert.match(html, />\/product\/ifilter-cold<\/a>\)\./)
})

test('review link helpers reject unsafe hrefs', () => {
  assert.equal(isSafeHref('/home'), true)
  assert.equal(isSafeHref('https://app.test:3000/home'), true)
  assert.equal(isSafeHref('javascript:alert(1)'), false)
  assert.equal(isSafeHref('//evil.test/home'), false)
  assert.equal(isSafeHref('http://user:pass@app.test/home'), false)
  assert.deepEqual(splitTrailingPunctuation('/home?preferences=phone.'), {
    token: '/home?preferences=phone',
    trailing: '.',
  })
})
