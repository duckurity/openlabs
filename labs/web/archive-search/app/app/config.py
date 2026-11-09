"""Operator configuration, read once at process startup."""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
AUTH_DB_PATH = str(DATA_DIR / "auth.sqlite")
CATALOG_DB_PATH = str(DATA_DIR / "catalog.sqlite")
SECURE_MODE = int(os.environ.get("SECURE_MODE", "0"))
if SECURE_MODE not in (0, 1):
    raise ValueError("SECURE_MODE must be 0 or 1")
TOKEN_EXPIRY_SECONDS = 3600
MAX_SEARCH_RESULTS = 50
MAX_SEARCH_QUERY_LENGTH = 200
# Public fictional lab credentials, not a production secret.
LAB_SEED_PASSWORD = os.environ.get("LAB_SEED_PASSWORD", "Archive2026-researcher")
