"""
Catalog access for the Backstage lab.

list_public_products() and search_products() are the only two queries the
API exposes against catalog.sqlite, and both open it read-only.

search_products() is the intended teaching point: in SECURE_MODE=0 it builds
the SQL statement by string concatenation, so the `name` clause's quoting
can be broken out of by crafted input. In SECURE_MODE=1 the same query uses
a bound parameter instead, which keeps the query structure fixed regardless
of what the search text contains.
"""

import sqlite3

from . import config
from .database import get_catalog_connection


class SearchError(Exception):
    """Raised when the catalog search cannot be completed."""


def list_public_products():
    conn = get_catalog_connection(read_only=True)
    try:
        rows = conn.execute(
            "SELECT id, name, category FROM products WHERE is_public = 1 ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def search_products(search_term: str):
    search_term = (search_term or "")[: config.MAX_SEARCH_QUERY_LENGTH]
    conn = get_catalog_connection(read_only=True)
    try:
        if config.SECURE_MODE:
            # Fixed: the search text is bound as a parameter. It can never
            # change the shape of the query, no matter what it contains.
            sql = (
                "SELECT id, name, category "
                "FROM products "
                "WHERE is_public = 1 "
                "AND name LIKE ? "
                "LIMIT ?"
            )
            rows = conn.execute(
                sql, ("%" + search_term + "%", config.MAX_SEARCH_RESULTS)
            ).fetchmany(config.MAX_SEARCH_RESULTS)
        else:
            # Intentionally vulnerable: the search text is concatenated
            # directly into the SQL statement. config.MAX_SEARCH_RESULTS is
            # a server-side constant, not user input, so it's safe to
            # concatenate on its own.
            sql = (
                "SELECT id, name, category "
                "FROM products "
                "WHERE is_public = 1 "
                "AND name LIKE '%" + search_term + "%' "
                "LIMIT " + str(config.MAX_SEARCH_RESULTS)
            )
            rows = conn.execute(sql).fetchmany(config.MAX_SEARCH_RESULTS)
    except sqlite3.Error:
        # Do not disclose raw SQLite messages or query text in either mode.
        raise SearchError("search could not be completed") from None
    finally:
        conn.close()
    results = [dict(row) for row in rows]
    if any(isinstance(value, bytes) for row in results for value in row.values()):
        raise SearchError("search could not be completed")
    return results
