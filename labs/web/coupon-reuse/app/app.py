"""Backstage Merch: an intentionally vulnerable, local training lab."""

import hmac
import os
import re
from pathlib import Path
import secrets
import sqlite3
import sys
from functools import wraps
from contextlib import closing

import click
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# Config and schema
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "instance"
LAB_FLAG = "duck{069f3cf090c9fe880b174c83ccf1172cde28232b}"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wallets (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    balance INTEGER NOT NULL CHECK(balance >= 0)
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price INTEGER NOT NULL CHECK(price > 0)
);
CREATE TABLE IF NOT EXISTS carts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0, 1))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_cart ON carts(user_id) WHERE paid = 0;
CREATE TABLE IF NOT EXISTS coupon_applications (
    id INTEGER PRIMARY KEY,
    cart_id INTEGER NOT NULL REFERENCES carts(id),
    code TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount = 50)
);
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY,
    cart_id INTEGER UNIQUE NOT NULL REFERENCES carts(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL CHECK(amount >= 0)
);
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def connect(path):
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db(path, secure):
    # One authored lab flag matches the public hash in lab.yml.
    # This service file is outside Flask's static directory.
    flag = LAB_FLAG
    if not re.fullmatch(r"duck\{[a-z0-9_]{16,40}\}", flag):
        raise ValueError("The service flag does not match the openlabs format")
    with closing(connect(path)) as db:
        os.chmod(path, 0o600)
        db.executescript(SCHEMA)
        db.execute("BEGIN IMMEDIATE")
        try:
            if not db.execute("SELECT 1 FROM runtime").fetchone():
                db.executemany(
                    "INSERT INTO runtime VALUES (?, ?)",
                    [
                        ("secret", secrets.token_hex(32)),
                        ("epoch", secrets.token_hex(32)),
                        ("flag", flag),
                    ],
                )
                db.execute(
                    "INSERT INTO users VALUES (1, ?, ?)",
                    ("customer", generate_password_hash("Backstage2026!")),
                )
                db.execute("INSERT INTO wallets VALUES (1, 100)")
                db.execute(
                    "INSERT INTO products VALUES (1, ?, 300)",
                    ("Exclusive Digital Pass",),
                )
            stored_flag = db.execute(
                "SELECT value FROM runtime WHERE key=?", ("flag",)
            ).fetchone()
            if not stored_flag or not hmac.compare_digest(stored_flag[0], flag):
                raise RuntimeError(
                    "Runtime belongs to another lab version. Stop workers and run reset."
                )
            if secure:
                # Database uniqueness is the fix. Existing duplicate data must be reset first.
                db.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS coupon_once ON coupon_applications(cart_id, code)"
                )
            else:
                db.execute("DROP INDEX IF EXISTS coupon_once")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return db.execute(
            "SELECT value FROM runtime WHERE key=?", ("secret",)
        ).fetchone()[0]


def runtime_config():
    mode = os.environ.get("SECURE_MODE", "0")
    if mode not in {"0", "1"}:
        raise ValueError("SECURE_MODE must be 0 or 1")
    return {
        "DB_PATH": os.environ.get("DB_PATH"),
        "DATA_DIR": os.environ.get("DATA_DIR", str(DEFAULT_DATA_DIR)),
        "SECURE_MODE": mode == "1",
    }


def database_path(config):
    # DB_PATH matches the reference lab. DATA_DIR remains a compatibility alias.
    path = config.get("DB_PATH") or Path(config["DATA_DIR"]) / "backstage.sqlite3"
    return Path(path).expanduser().resolve()


def prepare_runtime(path, secure, reset=False):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    previous_umask = os.umask(0o077)
    try:
        if reset:
            # Operator command only. Stop all web workers before resetting.
            path.unlink(missing_ok=True)
        return init_db(str(path), secure)
    finally:
        os.umask(previous_umask)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        **runtime_config(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=16384
    )
    if test_config:
        app.config.update(test_config)
    path = database_path(app.config)
    app.config["DATABASE"] = str(path)
    app.secret_key = prepare_runtime(path, app.config["SECURE_MODE"])

    def get_db():
        if "db" not in g:
            g.db = connect(app.config["DATABASE"])
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        if "db" in g:
            g.db.close()

    # -----------------------------------------------------------------------
    # Auth and request helpers
    # -----------------------------------------------------------------------
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_requests():
        if "user_id" in session:
            epoch = (
                get_db()
                .execute("SELECT value FROM runtime WHERE key=?", ("epoch",))
                .fetchone()[0]
            )
            if not hmac.compare_digest(session.get("epoch", ""), epoch):
                session.clear()
        if request.method == "POST":
            token = request.form.get("csrf_token", "")
            if not token or not hmac.compare_digest(
                token.encode(), session.get("csrf", "").encode()
            ):
                abort(400, "Invalid CSRF token")

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        )
        return response

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    def open_cart():
        return (
            get_db()
            .execute(
                "SELECT * FROM carts WHERE user_id=? AND paid=0", (session["user_id"],)
            )
            .fetchone()
        )

    def summary(cart):
        price = (
            get_db()
            .execute("SELECT price FROM products WHERE id=?", (cart["product_id"],))
            .fetchone()[0]
            if cart and cart["product_id"]
            else 0
        )
        discounts = (
            get_db()
            .execute(
                "SELECT code, amount FROM coupon_applications WHERE cart_id=? ORDER BY id",
                (cart["id"],),
            )
            .fetchall()
            if cart
            else []
        )
        return price, discounts, max(0, price - sum(row["amount"] for row in discounts))

    def reject_extra(allowed):
        if set(request.form) - set(allowed) - {"csrf_token"}:
            abort(400, "Unexpected form fields")

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------
    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("error.html", error=error), error.code

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            reject_extra({"username", "password"})
            user = (
                get_db()
                .execute(
                    "SELECT * FROM users WHERE username=?",
                    (request.form.get("username", ""),),
                )
                .fetchone()
            )
            if not user or not check_password_hash(
                user["password_hash"], request.form.get("password", "")
            ):
                return render_template("login.html", error="Invalid credentials"), 401
            session.clear()
            session["user_id"] = user["id"]
            session["epoch"] = (
                get_db()
                .execute("SELECT value FROM runtime WHERE key=?", ("epoch",))
                .fetchone()[0]
            )
            return redirect(url_for("shop"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        reject_extra(set())
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def home():
        return redirect(url_for("shop"))

    @app.get("/shop")
    @login_required
    def shop():
        product = get_db().execute("SELECT * FROM products WHERE id=1").fetchone()
        balance = (
            get_db()
            .execute(
                "SELECT balance FROM wallets WHERE user_id=?", (session["user_id"],)
            )
            .fetchone()[0]
        )
        return render_template("shop.html", product=product, balance=balance)

    @app.post("/cart/items")
    @login_required
    def add_item():
        reject_extra({"product_id", "quantity"})
        if (
            request.form.get("product_id") != "1"
            or request.form.get("quantity", "1") != "1"
        ):
            abort(400, "Choose the available product with quantity 1")
        database = get_db()
        database.execute("BEGIN IMMEDIATE")
        try:
            cart = open_cart()
            # One pass per unpaid cart; paid carts are never selected or changed.
            if cart:
                database.execute(
                    "UPDATE carts SET product_id=1 WHERE id=? AND user_id=? AND paid=0",
                    (cart["id"], session["user_id"]),
                )
            else:
                database.execute(
                    "INSERT INTO carts(user_id, product_id) VALUES (?, 1)",
                    (session["user_id"],),
                )
            database.commit()
        except Exception:
            database.rollback()
            raise
        return redirect(url_for("cart"))

    @app.get("/cart")
    @login_required
    def cart():
        current = open_cart()
        price, discounts, total = summary(current)
        # Only a persisted, completed purchase owned by this session unlocks the flag.
        purchase = (
            get_db()
            .execute(
                "SELECT * FROM purchases WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (session["user_id"],),
            )
            .fetchone()
        )
        flag = (
            get_db()
            .execute("SELECT value FROM runtime WHERE key=?", ("flag",))
            .fetchone()[0]
            if purchase
            else None
        )
        return render_template(
            "cart.html",
            cart=current,
            price=price,
            discounts=discounts,
            total=total,
            purchase=purchase,
            flag=flag,
        )

    @app.post("/cart/coupon")
    @login_required
    def apply_coupon():
        reject_extra({"code"})
        if request.form.get("code", "") != "WELCOME50":
            abort(400, "Invalid coupon")
        database = get_db()
        database.execute("BEGIN IMMEDIATE")
        try:
            current = open_cart()
            if not current or not current["product_id"]:
                abort(409, "No unpaid cart with an item")
            # INTENTIONAL FLAW: vulnerable mode inserts without enforcing single use.
            # FIX: secure mode's unique (cart_id, code) index rejects duplicate inserts.
            database.execute(
                "INSERT INTO coupon_applications(cart_id, code, amount) VALUES (?, ?, 50)",
                (current["id"], "WELCOME50"),
            )
            database.commit()
        except sqlite3.IntegrityError:
            database.rollback()
            abort(409, "Coupon already applied to this cart")
        except Exception:
            database.rollback()
            raise
        return redirect(url_for("cart"))

    @app.post("/checkout")
    @login_required
    def checkout():
        reject_extra(set())
        database = get_db()
        database.execute("BEGIN IMMEDIATE")
        try:
            current = open_cart()
            if not current or not current["product_id"]:
                abort(409, "No unpaid cart with an item")
            _, _, total = summary(current)
            result = database.execute(
                "UPDATE wallets SET balance=balance-? WHERE user_id=? AND balance>=?",
                (total, session["user_id"], total),
            )
            if result.rowcount != 1:
                abort(409, "Insufficient wallet balance")
            database.execute(
                "INSERT INTO purchases(cart_id, user_id, amount) VALUES (?, ?, ?)",
                (current["id"], session["user_id"], total),
            )
            database.execute(
                "UPDATE carts SET paid=1 WHERE id=? AND user_id=? AND paid=0",
                (current["id"], session["user_id"]),
            )
            database.commit()
        except Exception:
            database.rollback()
            raise
        flash("Payment successful. Your Exclusive Digital Pass is ready.")
        return redirect(url_for("cart"))

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    @app.cli.command("reset")
    def reset():
        """Reset runtime state. Stop all web workers before invoking this command."""
        # Reset progress and session keys. Keep the lab flag aligned with lab.yml.
        app.secret_key = prepare_runtime(path, app.config["SECURE_MODE"], reset=True)
        click.echo("Reset complete. Restart web workers before serving requests.")

    return app


# ---------------------------------------------------------------------------
# Local entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if sys.argv[1:] == ["reset"]:
        config = runtime_config()
        # Reset before constructing the factory, including when old duplicates
        # would prevent secure startup. Never reset from an HTTP request.
        prepare_runtime(database_path(config), config["SECURE_MODE"], reset=True)
        print("Reset complete. Restart web workers before serving requests.")
    elif sys.argv[1:]:
        raise SystemExit("Usage: python app/app.py [reset]")
    else:
        create_app().run(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=False,
        )
