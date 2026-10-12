"""Anonymous cinema archive. Only search contains intentional SQL injection."""
from __future__ import annotations

from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request

from . import db
from .seed import DEFAULT_STATE


def create_app(database: Path | None = None) -> Flask:
    application = Flask(__name__)
    application.config.update(DEBUG=False, TESTING=False, MAX_CONTENT_LENGTH=8192)
    path = database or DEFAULT_STATE / "archive.sqlite"

    @application.after_request
    def harden(response):
        response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/")
    def index():
        return render_template("catalogue.html", films=db.catalogue(path), query="", searched=False, error=None)

    @application.get("/search")
    def search():
        if len(request.query_string) > 2048 or set(request.args) - {"q"} or len(request.args.getlist("q")) > 1:
            return render_template("catalogue.html", films=[], query="", searched=True, error="Search could not be completed."), 400
        query = request.args.get("q", "")
        try:
            results = db.search(path, query)
        except db.QueryRejected:
            # Do not echo rejected SQL, raw SQLite exceptions or filesystem paths.
            return render_template("catalogue.html", films=[], query="", searched=True, error="Search could not be completed."), 400
        return render_template("catalogue.html", films=results, query=query, searched=True, error=None)

    @application.get("/films/<int:film_id>")
    def details(film_id: int):
        record = db.film(path, film_id)
        if record is None:
            abort(404)
        back_query = request.args.get("q") if len(request.args.getlist("q")) == 1 else None
        if back_query is not None and (len(back_query) > 512 or "\x00" in back_query):
            back_query = None
        return render_template("film.html", film=record, back_query=back_query)

    @application.get("/health")
    def health():
        db.execute(path, "SELECT 1")
        return jsonify(service="last-reel", status="ok")

    @application.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="This record is not in the public catalogue."), 404

    @application.errorhandler(405)
    def method_not_allowed(error):
        return render_template("error.html", code=405, message="Use the public catalogue search form."), 405

    @application.errorhandler(500)
    def unavailable(error):
        return render_template("error.html", code=500, message="The archive is unavailable. Please try again."), 500

    return application
