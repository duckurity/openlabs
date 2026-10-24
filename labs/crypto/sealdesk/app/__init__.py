"""SealDesk's small HTTP surface and intentionally vulnerable receipt checker."""

from __future__ import annotations

import hmac
import re
from pathlib import Path
from typing import Any, Mapping

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from app.crypto import DamagedEnvelope, ReceiptFormatError, UntrustedEnvelope, check_receipt
from app.state import RuntimeState, STATE_DIR, STATE_FILENAME, load_state

_ACCESS_CODE = re.compile(r"[0-9a-f]{32}\Z")
_DOCUMENT_TEXT = (
    "The harbor records team will maintain the east archive during the autumn "
    "service window. This copy is for the named recipient only."
)


def _api_response(payload: dict[str, Any], status: int):
    return jsonify(payload), status


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build the app with either a private disk state or an injected test state."""
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=8192, TESTING=False)
    if config is not None:
        app.config.update(config)

    runtime_state = app.config.get("RUNTIME_STATE")
    if not isinstance(runtime_state, RuntimeState):
        state_dir = Path(app.config.get("STATE_DIR", STATE_DIR))
        runtime_state = load_state(state_dir / STATE_FILENAME)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        return _api_response({
            "status": "request_too_large",
            "message": "Request is too large.",
        }, 413)

    @app.get("/")
    def index():
        return render_template("index.html", case=runtime_state.public_case())

    @app.get("/health")
    def health():
        return jsonify({"service": "sealdesk", "status": "ok"})

    @app.get("/case")
    def public_case():
        return jsonify(runtime_state.public_case())

    @app.post("/api/receipts/check")
    def check_public_receipt():
        payload = request.get_json(silent=True)
        if payload is None:
            return _api_response({
                "status": "invalid_receipt",
                "message": "Receipt is not in the expected format.",
            }, 400)
        try:
            check_receipt(payload, runtime_state.encryption_key, runtime_state.mac_key)
        except ReceiptFormatError:
            return _api_response({
                "status": "invalid_receipt",
                "message": "Receipt is not in the expected format.",
            }, 400)
        except DamagedEnvelope:
            return _api_response({
                "status": "damaged_envelope",
                "message": "Receipt could not be decoded.",
            }, 422)
        except UntrustedEnvelope:
            return _api_response({
                "status": "untrusted_envelope",
                "message": "Receipt could not be trusted.",
            }, 422)
        return _api_response({
            "status": "valid_receipt",
            "message": "Receipt accepted. The document can be opened separately.",
        }, 200)

    @app.post("/api/documents/open")
    def open_document():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {"document_id", "access_code"}:
            return _document_unavailable()
        document_id = payload["document_id"]
        access_code = payload["access_code"]
        if (
            not isinstance(document_id, str)
            or not document_id.isascii()
            or not isinstance(access_code, str)
            or not _ACCESS_CODE.fullmatch(access_code)
        ):
            return _document_unavailable()

        document_matches = hmac.compare_digest(
            document_id.encode("utf-8"), runtime_state.document_id.encode("utf-8")
        )
        code_matches = hmac.compare_digest(
            access_code.encode("ascii"), runtime_state.access_code.encode("ascii")
        )
        if not (document_matches and code_matches):
            return _document_unavailable()
        return _api_response({
            "status": "document_opened",
            "document": {
                "title": runtime_state.public_case()["document_title"],
                "text": _DOCUMENT_TEXT,
            },
            "flag": runtime_state.flag,
        }, 200)

    return app


def _document_unavailable():
    return _api_response({
        "status": "document_unavailable",
        "message": "The document could not be opened.",
    }, 403)
