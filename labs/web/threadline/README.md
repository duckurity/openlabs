# ThreadLine — Broken Boundaries

**Category:** Web / API Security
**Difficulty:** Medium

---

## Brief

ThreadLine is an online clothing store rolling out a new REST API. During a
private beta, a customer's account was quietly given a **loyalty retention
offer** after they threatened to close their account. The offer was never
meant to be public, and it was never meant to be discoverable by anyone but
the customer themselves.

You've been dropped into the beta as a regular shopper with one goal:
**get the Premium Leather Jacket for free**, the way it was never supposed to
happen.

---

## What you're given

A running instance of the ThreadLine API at:

```
http://<target-host>:8000/api/v1
```

There is no web frontend — this is an API-only challenge. Use `curl`,
`httpie`, Postman, Burp Repeater, or a script; whatever you're comfortable
driving raw HTTP requests with.

## Setup

1. Register your own account:
   ```
   POST /api/v1/auth/register
   { "username": "...", "email": "...", "password": "..." }
   ```
2. Log in — the API uses a session cookie, not a bearer token:
   ```
   POST /api/v1/auth/login
   { "email": "...", "password": "..." }
   ```
3. Explore from there. Every account starts with a small balance, but that's
   not enough to buy anything on its own.

## Endpoints (non-exhaustive — some may not matter, some might matter a lot)

| Method | Path                          | Notes                         |
|--------|-------------------------------|--------------------------------|
| POST   | `/api/v1/auth/register`       | Create an account              |
| POST   | `/api/v1/auth/login`          | Get a session cookie           |
| POST   | `/api/v1/auth/logout`         | Invalidate your session        |
| GET    | `/api/v1/users/<id>`          | View a user's public profile   |
| GET    | `/api/v1/products`            | List products                  |
| GET    | `/api/v1/products/<id>`       | View a single product          |
| POST   | `/api/v1/coupons`             | Request a coupon by email      |
| POST   | `/api/v1/cart/items`          | Add a product to your cart     |
| POST   | `/api/v1/cart/apply-coupon`   | Apply a coupon to your cart    |
| POST   | `/api/v1/orders`              | Checkout your cart             |
| GET    | `/api/v1/health`              | Liveness check                 |

## Goal

Get a cart's `final_price` down to **0**, then check out. If you got there
the *right* way, checkout will hand you a flag.

See [how to play](/play) for the usual solve loop.

## Rules

- Don't attack anything outside this container (it has no internet access
  anyway).
- Don't brute-force passwords or run heavy fuzzing that could take the
  service down for other players — this is a logic challenge, not a
  denial-of-service exercise.
- The flag format is `duck{...}`.

## Hints

<details>
<summary>Hint 1</summary>

Not every endpoint that requires "being logged in" also checks that you're
looking at *your own* data.

</details>

<details>
<summary>Hint 2</summary>

If an endpoint tells you "no offer found for this email," ask yourself
exactly how it's comparing the email you sent against the one it has on
file.

</details>

<details>
<summary>Hint 3</summary>

One coupon might not be enough to hit zero. Is there anything stopping you
from having more than one?

</details>

---

Good luck — and remember: the interesting bug is rarely the loudest one.
