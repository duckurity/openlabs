"""Seed once before starting the worker processes. Never log request queries."""

import os

import seed


if __name__ == "__main__":
    seed.main()
    os.execvp("gunicorn", [
        "gunicorn", "--no-control-socket", "--bind=0.0.0.0:8080", "--workers=2", "--threads=2",
        "--timeout=15", "--access-logfile=/dev/null", "app:create_app()",
    ])
