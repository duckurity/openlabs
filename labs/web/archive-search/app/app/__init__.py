import sqlite3

from flask import Flask, g, jsonify, render_template, request

from . import auth, catalog, config
from .database import get_auth_connection, get_catalog_connection


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        try:
            for connect, query in (
                (get_auth_connection, "SELECT COUNT(*) FROM users"),
                (get_catalog_connection, "SELECT COUNT(*) FROM assessment_records"),
            ):
                conn = connect()
                try:
                    if conn.execute(query).fetchone()[0] < 1:
                        return jsonify({"status": "unavailable"}), 503
                finally:
                    conn.close()
        except sqlite3.Error:
            return jsonify({"status": "unavailable"}), 503
        return jsonify({"status": "ok"}), 200

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "a JSON object is required"}), 400
        username = data.get("username", "")
        password = data.get("password", "")
        if (not isinstance(username, str) or not isinstance(password, str)
                or not username or not password or len(username) > 128
                or len(password) > 1024):
            return jsonify({"error": "username and password are required"}), 400
        user_id = auth.authenticate(username, password)
        if user_id is None:
            return jsonify({"error": "invalid credentials"}), 401
        token = auth.create_session(user_id)
        return jsonify({"token": token, "expires_in": config.TOKEN_EXPIRY_SECONDS}), 200

    @app.get("/api/me")
    @auth.require_auth
    def me():
        username = auth.get_username(g.user_id)
        return jsonify({"id": g.user_id, "username": username}), 200

    @app.get("/api/products")
    @auth.require_auth
    def products():
        return jsonify({"results": catalog.list_public_products()}), 200

    @app.get("/api/search")
    @auth.require_auth
    def search():
        q = request.args.get("q", "")
        try:
            results = catalog.search_products(q)
        except catalog.SearchError:
            return jsonify({"error": "search could not be completed"}), 400
        return jsonify({"results": results}), 200

    @app.post("/api/logout")
    @auth.require_auth
    def logout():
        auth.invalidate_token(g.token)
        return jsonify({"status": "logged out"}), 200

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify({"error": "method not allowed"}), 405

    @app.errorhandler(413)
    def request_too_large(_err):
        return jsonify({"error": "request too large"}), 413

    return app
