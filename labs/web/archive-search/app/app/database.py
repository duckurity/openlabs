"""
Database access for the Backstage lab.

Two separate SQLite files are used on purpose:

- auth.sqlite    accounts and sessions
- catalog.sqlite public products and the protected assessment record

The search endpoint (app/catalog.py) only ever opens catalog.sqlite, and
opens it read-only. That keeps the intentional SQL injection in the search
endpoint scoped to archive disclosure — it cannot be used to read or touch
account passwords or session tokens, and it cannot write to the catalog
database either.
"""

import sqlite3
from pathlib import Path

from . import config


def get_auth_connection():
    conn = sqlite3.connect(config.AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_catalog_connection(read_only=True):
    """Open catalog.sqlite. Callers doing anything other than seeding the
    database should always use read_only=True."""
    if read_only:
        uri = Path(config.CATALOG_DB_PATH).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(config.CATALOG_DB_PATH)
    conn.row_factory = sqlite3.Row
    if read_only:
        conn.execute("PRAGMA query_only = ON")
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 64 * 1024)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 4096)
        remaining = 1000

        def budget():
            nonlocal remaining
            remaining -= 1
            return int(remaining <= 0)

        conn.set_progress_handler(budget, 1000)
    return conn


def init_auth_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()


def init_catalog_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            is_public INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS assessment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            secret_value TEXT NOT NULL
        );
        """
    )
    conn.commit()
