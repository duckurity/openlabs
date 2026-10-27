import hmac
import os
import secrets
import threading
import time
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

app = Flask(__name__)

APK_DIR = Path(app.root_path) / "static" / "downloads"

ARCHIVE_RECORD_ID = "ARCHIVE-07"
ARCHIVE_ACCESS_CODE = "7391"

NONCE_TTL_SECONDS = 60
issued_nonces = {}
nonce_lock = threading.Lock()


def resolve_flag() -> str:
    value = os.environ.get("FLAG", "").strip()

    if not value or value.startswith("REPLACE_ME_"):
        raise RuntimeError(
            "FLAG is not configured. Set FLAG in the environment."
        )

    return value


FLAG = resolve_flag()


def cleanup_nonces(now: float) -> None:
    expired = [
        nonce
        for nonce, expires_at in issued_nonces.items()
        if expires_at <= now
    ]

    for nonce in expired:
        issued_nonces.pop(nonce, None)


@app.get("/")
def index():
    apk_exists = (APK_DIR / "duckwebview.apk").is_file()
    return render_template("index.html", apk_exists=apk_exists)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/archive/challenge")
def create_archive_challenge():
    now = time.monotonic()
    nonce = secrets.token_urlsafe(24)

    with nonce_lock:
        cleanup_nonces(now)
        issued_nonces[nonce] = now + NONCE_TTL_SECONDS

    return jsonify({
        "nonce": nonce,
        "expires_in": NONCE_TTL_SECONDS,
    })


@app.post("/api/archive/query")
def query_archive():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    record_id = str(data.get("record_id", ""))
    access_code = str(data.get("access_code", ""))
    nonce = str(data.get("nonce", ""))

    if not nonce:
        return jsonify({"error": "Missing challenge nonce"}), 400

    now = time.monotonic()

    with nonce_lock:
        cleanup_nonces(now)
        expires_at = issued_nonces.pop(nonce, None)

    if expires_at is None or expires_at <= now:
        return jsonify({
            "error": "Invalid, expired, or already used nonce"
        }), 403

    valid_record = hmac.compare_digest(
        record_id,
        ARCHIVE_RECORD_ID,
    )
    valid_code = hmac.compare_digest(
        access_code,
        ARCHIVE_ACCESS_CODE,
    )

    if not (valid_record and valid_code):
        return jsonify({
            "error": "Archive record not found or access denied"
        }), 403

    return jsonify({
        "status": "success",
        "record": record_id,
        "flag": FLAG,
    })


@app.get("/download/duckwebview.apk")
def download_apk():
    apk = APK_DIR / "duckwebview.apk"

    if not apk.is_file():
        abort(
            404,
            description=(
                "APK not built yet. Build the Android project and copy "
                "the APK to src/static/downloads/duckwebview.apk."
            ),
        )

    return send_from_directory(
        APK_DIR,
        "duckwebview.apk",
        as_attachment=True,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)