"""
ThreadLine — Broken Boundaries (CTF Challenge)

Intended vulnerabilities (see design document):
  1. BOLA        -> GET /api/v1/users/<id>
  2. Business Logic (prefix matching on discount offers)
                  -> POST /api/v1/coupons
  3. Business Logic (unrestricted coupon stacking, no discount cap)
                  -> POST /api/v1/cart/apply-coupon + POST /api/v1/orders

Everything else (sessions, SQLi, coupon replay, coupon sharing) is
intentionally implemented SECURELY to keep the challenge focused
(see "Minimal Noise" checklist in the design document).
"""
import sqlite3
import os
import secrets
import hashlib
import string
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify, g

DB_PATH = os.environ.get("DB_PATH", "/data/threadline.db")

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
log = logging.getLogger("chal")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_session_token() -> str:
    return secrets.token_hex(24)


def generate_coupon_code() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SAVE10-{suffix}"


def get_authenticated_user():
    token = request.cookies.get("session")
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT users.* FROM sessions "
        "JOIN users ON users.id = sessions.user_id "
        "WHERE sessions.token = ?",
        (token,),
    ).fetchone()
    return row


def require_auth():
    user = get_authenticated_user()
    if user is None:
        return None, (jsonify({"error": "Authentication required"}), 401)
    return user, None


@app.route("/api/v1/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "username, email and password are required"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    cur = db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password)),
    )
    db.commit()

    return jsonify({"id": cur.lastrowid, "username": username, "email": email}), 201


@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user is None or user["password_hash"] != hash_password(password or ""):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_session_token()
    db.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user["id"], datetime.utcnow().isoformat()),
    )
    db.commit()

    resp = jsonify({"message": "Login successful"})
    resp.set_cookie("session", token, httponly=True, path="/")
    return resp, 200


@app.route("/api/v1/auth/logout", methods=["POST"])
def logout():
    token = request.cookies.get("session")
    if token:
        db = get_db()
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()
    resp = jsonify({"message": "Logged out"})
    resp.set_cookie("session", "", expires=0, path="/")
    return resp, 200


# --------------------------------------------------------------------------
# Users — INTENDED BOLA HERE
# No ownership check at all: any authenticated user can fetch any other
# user's public profile just by changing the id. No allowlist, no special
# casing — this is the genuine missing-authorization-check flaw.
# --------------------------------------------------------------------------
@app.route("/api/v1/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    target = db.execute(
        "SELECT id, username, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if target is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"id": target["id"], "username": target["username"], "email": target["email"]}), 200


@app.route("/api/v1/products", methods=["GET"])
def list_products():
    db = get_db()
    rows = db.execute("SELECT id, name, price FROM products").fetchall()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/v1/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    db = get_db()
    row = db.execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(dict(row)), 200


# --------------------------------------------------------------------------
# Coupons — INTENDED BUSINESS LOGIC FLAW HERE (prefix matching)
# --------------------------------------------------------------------------
@app.route("/api/v1/coupons", methods=["POST"])
def create_coupon():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if "@" not in email:
        return jsonify({"error": "No active offer found for this email"}), 404

    local_part = email.split("@")[0]
    domain = email.split("@")[1]

    matched_prefix = local_part[:6]
    like_pattern = f"{matched_prefix}%@{domain}"

    db = get_db()
    offer = db.execute(
        "SELECT * FROM offers WHERE exact_email LIKE ?", (like_pattern,)
    ).fetchone()

    if offer is None:
        return jsonify({"error": "No active offer found for this email"}), 404

    existing = db.execute(
        "SELECT id FROM coupons WHERE linked_email = ?", (email,)
    ).fetchone()
    if existing:
        return jsonify({"error": "A coupon for this email already exists"}), 409

    code = generate_coupon_code()
    try:
        cur = db.execute(
            "INSERT INTO coupons (code, discount_amount, linked_email, owner_user_id, used) "
            "VALUES (?, ?, ?, ?, 0)",
            (code, offer["discount_amount"], email, user["id"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"error": "A coupon for this email already exists"}), 409

    return jsonify(
        {
            "id": cur.lastrowid,
            "code": code,
            "discount_amount": offer["discount_amount"],
            "linked_email": email,
        }
    ), 201


def get_or_create_cart(db, user_id):
    cart = db.execute("SELECT * FROM carts WHERE user_id = ?", (user_id,)).fetchone()
    if cart is None:
        cur = db.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
        db.commit()
        cart = db.execute("SELECT * FROM carts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return cart


def cart_totals(db, cart_id):
    items = db.execute(
        "SELECT price FROM cart_items WHERE cart_id = ?", (cart_id,)
    ).fetchall()
    subtotal = sum(i["price"] for i in items)

    discount = db.execute(
        "SELECT COALESCE(SUM(discount_amount), 0) AS total "
        "FROM coupons WHERE applied_to_cart_id = ? AND used = 1",
        (cart_id,),
    ).fetchone()["total"]

    final_price = max(0, subtotal - discount)
    return subtotal, discount, final_price


@app.route("/api/v1/cart/items", methods=["POST"])
def add_cart_item():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")

    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        return jsonify({"error": "Product not found"}), 404

    cart = get_or_create_cart(db, user["id"])
    db.execute(
        "INSERT INTO cart_items (cart_id, product_id, price) VALUES (?, ?, ?)",
        (cart["id"], product["id"], product["price"]),
    )
    db.commit()

    subtotal, discount, final_price = cart_totals(db, cart["id"])
    return jsonify({"cart_id": cart["id"], "subtotal": subtotal, "final_price": final_price}), 200


@app.route("/api/v1/cart/apply-coupon", methods=["POST"])
def apply_coupon():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    coupon_code = data.get("coupon_code")

    db = get_db()
    cart = get_or_create_cart(db, user["id"])

    coupon = db.execute("SELECT * FROM coupons WHERE code = ?", (coupon_code,)).fetchone()
    if coupon is None:
        return jsonify({"error": "Coupon not found"}), 404

    if coupon["owner_user_id"] != user["id"]:
        return jsonify({"error": "Coupon does not belong to this user"}), 403

    cur = db.execute(
        "UPDATE coupons SET used = 1, applied_to_cart_id = ? "
        "WHERE id = ? AND owner_user_id = ? AND used = 0",
        (cart["id"], coupon["id"], user["id"]),
    )
    db.commit()

    if cur.rowcount == 0:
        return jsonify({"error": "Coupon already used or invalid"}), 409

    subtotal, discount, final_price = cart_totals(db, cart["id"])

    return jsonify(
        {"subtotal": subtotal, "total_discount": discount, "final_price": final_price}
    ), 200


def resolve_flag() -> str:
    return os.environ.get("FLAG") or "flag_not_configured"


FLAG = resolve_flag()
TARGET_EMAIL = "Hack25@gmail.com"  # must match seed.py


@app.route("/api/v1/orders", methods=["POST"])
def create_order():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    cart_id = data.get("cart_id")

    db = get_db()
    cart = db.execute(
        "SELECT * FROM carts WHERE id = ? AND user_id = ?", (cart_id, user["id"])
    ).fetchone()
    if cart is None:
        return jsonify({"error": "Cart not found"}), 404

    subtotal, discount, final_price = cart_totals(db, cart["id"])

    if subtotal == 0:
        return jsonify({"error": "Cart is empty"}), 400

    if final_price > 0:
        return jsonify(
            {
                "error": "Insufficient balance to complete this order",
                "subtotal": subtotal,
                "total_discount": discount,
                "final_price": final_price,
            }
        ), 402

    exact_match_coupon = db.execute(
        "SELECT id FROM coupons WHERE applied_to_cart_id = ? AND used = 1 AND linked_email = ?",
        (cart["id"], TARGET_EMAIL),
    ).fetchone()

    flag_awarded = 1 if exact_match_coupon is not None else 0

    cur = db.execute(
        "INSERT INTO orders (user_id, cart_id, final_price, status, flag_awarded) "
        "VALUES (?, ?, ?, 'completed', ?)",
        (user["id"], cart["id"], final_price, flag_awarded),
    )
    db.commit()

    response = {
        "order_id": cur.lastrowid,
        "status": "completed",
        "final_price": final_price,
    }

    if flag_awarded:
        response["flag"] = FLAG
    else:
        response["message"] = "Order completed."

    return jsonify(response), 201


@app.route("/api/v1/health", methods=["GET"])
def health():
    try:
        db = get_db()
        db.execute("SELECT 1").fetchone()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    raise SystemExit("Run with gunicorn: gunicorn -c gunicorn.conf.py app:app")
