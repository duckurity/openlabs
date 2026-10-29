"""
Authentication for the Backstage lab.

- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes.
- Sessions use an opaque random bearer token (not a JWT). Only the SHA-256
  hash of the token is stored server-side, and every authenticated request
  checks expiry.

All queries in this module are parameterized. The intentional vulnerability
for this lab lives only in app/catalog.py's search endpoint.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import g, jsonify, request

from . import config
from .database import get_auth_connection

PBKDF2_ITERATIONS = 390_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"{salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected_hex = password_hash.split("$", 1)
    except ValueError:
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(derived.hex(), expected_hex)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate(username: str, password: str):
    """Return the user id on success, None on failure."""
    conn = get_auth_connection()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return row["id"]


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    token_hash = _hash_token(token)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=config.TOKEN_EXPIRY_SECONDS)
    ).isoformat()
    conn = get_auth_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_id_for_token(token: str):
    if not token:
        return None
    token_hash = _hash_token(token)
    conn = get_auth_connection()
    try:
        row = conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return row["user_id"]


def invalidate_token(token: str) -> None:
    if not token:
        return
    token_hash = _hash_token(token)
    conn = get_auth_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
    finally:
        conn.close()


def get_username(user_id: int):
    conn = get_auth_connection()
    try:
        row = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    return row["username"] if row else None


def _extract_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip()


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = _extract_bearer_token()
        user_id = get_user_id_for_token(token)
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        g.user_id = user_id
        g.token = token
        return view(*args, **kwargs)

    return wrapped
