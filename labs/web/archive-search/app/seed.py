"""Create fictional data using the configured submission flag."""

import os

from app import auth, config
from app.database import get_auth_connection, get_catalog_connection
from app.database import init_auth_schema, init_catalog_schema

DEFAULT_PRODUCTS = [
    ("Conference Hoodie", "apparel"),
    ("Speaker Notebook", "stationery"),
    ("Backstage Mug", "accessories"),
]


def seed_auth():
    conn = get_auth_connection()
    try:
        init_auth_schema(conn)
        with conn:
            if not conn.execute("SELECT id FROM users WHERE username = ?", ("researcher",)).fetchone():
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("researcher", auth.hash_password(config.LAB_SEED_PASSWORD)),
                )
    finally:
        conn.close()


def seed_catalog():
    conn = get_catalog_connection(read_only=False)
    try:
        init_catalog_schema(conn)
        with conn:
            if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO products (name, category, is_public) VALUES (?, ?, 1)",
                    DEFAULT_PRODUCTS,
                )
            if conn.execute("SELECT COUNT(*) FROM assessment_records").fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO assessment_records (label, secret_value) VALUES (?, ?)",
                    ("Q3 Internal Assessment", os.environ.get("FLAG", "duck{689ffeeb4364345ff7db83ed912d4b09}")),
                )
    finally:
        conn.close()


def main():
    # New databases and their directory are private to the runtime account.
    os.umask(0o077)
    os.makedirs(config.DATA_DIR, mode=0o700, exist_ok=True)
    seed_auth()
    seed_catalog()
    print("Archive Search initialized.")


if __name__ == "__main__":
    main()
