"""Doppelganger challenge application.

The service deliberately models two parser mismatches: the edge WAF inspects
the first duplicate JSON member while the backend keeps the last one, and the
HTML blocklist only recognizes a literal space, ``>`` or ``/`` after a tag
name. A private admin bot reviews every stored note in a real browser.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, make_response, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.getenv("SAFENOTES_DATABASE", BASE_DIR / "safenotes.sqlite3"))


def load_flag() -> str:
    """Read the flag from the environment or from the bundled flag file."""
    configured = os.getenv("FLAG", "").strip()
    if configured:
        return configured
    flag_file = Path(os.getenv("FLAG_FILE", BASE_DIR / "flag.txt"))
    return flag_file.read_text(encoding="utf-8").strip()


FLAG = load_flag()
PLAYER_TOKEN = os.getenv("PLAYER_TOKEN", "local-player")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "local-admin-bot")


BLOCKED_TAGS = [
    "script", "img", "iframe", "object", "embed", "svg", "video", "audio",
    "details", "body", "marquee", "select", "input", "textarea", "style",
    "link", "meta", "base", "form", "math",
]
BLOCKED_EVENTS = [
    "onerror", "onload", "onclick", "onmouseover", "ontoggle", "onfocus",
    "onblur", "onanimationstart", "onanimationend", "onbegin", "onpointerover",
    "onwheel", "onauxclick", "onbeforetoggle", "onpageshow", "onresize",
    "onscroll", "ondrag", "oncopy", "onpaste",
]


@contextmanager
def get_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def waf_check(raw_body: str) -> bool:
    """Check only the first content member, matching the challenge WAF."""
    try:
        pairs = json.loads(raw_body, object_pairs_hook=lambda items: items)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False

    if not isinstance(pairs, list):
        return False

    for key, value in pairs:
        if key == "content":
            if re.search(r"<|onerror|script", str(value), re.IGNORECASE):
                return False
            return True
    return False


def sanitize(content: str) -> str | None:
    """Apply the deliberately incomplete blocklist from the challenge."""
    lowered = content.lower()
    for tag in BLOCKED_TAGS:
        if f"<{tag} " in lowered or f"<{tag}>" in lowered or f"<{tag}/" in lowered:
            return None
    for event in BLOCKED_EVENTS:
        if f"{event}=" in lowered:
            return None
    return content


def extract_flag(captured: str) -> str | None:
    if captured == FLAG:
        return FLAG
    cookies = SimpleCookie()
    try:
        cookies.load(captured)
    except (TypeError, ValueError):
        return None
    admin_cookie = cookies.get("admin_session")
    if admin_cookie and admin_cookie.value == FLAG:
        return FLAG
    return None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(JSON_SORT_KEYS=False)
    init_db()

    @app.get("/")
    def index():
        return render_template("index.html", player_token=PLAYER_TOKEN)

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.post("/api/notes")
    def create_note():
        raw_body = request.get_data(as_text=True)
        if not waf_check(raw_body):
            return jsonify(status="rejected", error="Blocked by WAF"), 403

        try:
            data: dict[str, Any] = json.loads(raw_body)
            content = data["content"]
        except (TypeError, ValueError, json.JSONDecodeError, KeyError):
            return jsonify(status="rejected", error="Invalid JSON"), 400

        if not isinstance(content, str):
            return jsonify(status="rejected", error="Invalid content"), 400

        sanitized = sanitize(content)
        if sanitized is None:
            return jsonify(status="rejected", error="Blocklist detected")

        with get_db() as connection:
            cursor = connection.execute(
                "INSERT INTO notes (content) VALUES (?)", (sanitized,)
            )
            note_id = cursor.lastrowid
        return jsonify(status="created", note_id=str(note_id)), 201

    @app.get("/api/notes")
    def list_notes():
        with get_db() as connection:
            notes = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, content, created_at FROM notes ORDER BY id"
                )
            ]
        return jsonify(notes=notes)

    @app.get("/admin/dashboard")
    def admin_dashboard():
        if not secrets.compare_digest(
            request.headers.get("X-Admin-Bot-Token", ""), ADMIN_BOT_TOKEN
        ):
            return jsonify(status="forbidden"), 403

        with get_db() as connection:
            notes = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, content, created_at FROM notes ORDER BY id"
                )
            ]

        response = make_response(render_template("admin.html", notes=notes))
        response.set_cookie("admin_session", FLAG, httponly=False, samesite="Lax")
        return response

    @app.route("/api/submit-flag", methods=["GET", "POST"])
    def submit_flag():
        token = request.args.get("token") or request.form.get("token")
        captured = request.args.get("c") or request.form.get("c")
        if token != PLAYER_TOKEN or not captured:
            return jsonify(status="rejected"), 403
        solved_flag = extract_flag(captured)
        if solved_flag is None:
            return jsonify(status="rejected"), 400

        with get_db() as connection:
            connection.execute(
                "INSERT INTO captures (token, value) VALUES (?, ?)",
                (token, solved_flag),
            )
        return jsonify(status="solved", token=token)

    @app.get("/api/collect/<token>")
    def collect(token: str):
        captured = request.args.get("c", "")
        if token != PLAYER_TOKEN or not captured:
            return jsonify(status="rejected"), 403
        with get_db() as connection:
            connection.execute(
                "INSERT INTO captures (token, value) VALUES (?, ?)",
                (token, captured),
            )
        return jsonify(status="captured")

    @app.get("/api/solved")
    def solved():
        with get_db() as connection:
            capture = connection.execute(
                "SELECT token, value, created_at FROM captures "
                "WHERE token = ? ORDER BY id DESC LIMIT 1",
                (PLAYER_TOKEN,),
            ).fetchone()
        return jsonify(
            solved=bool(capture), capture=dict(capture) if capture else None
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
