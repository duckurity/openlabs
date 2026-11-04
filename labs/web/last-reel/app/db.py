"""Intentional search SQLi, isolated behind bounded read-only SQLite controls."""
from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from pathlib import Path

MAX_QUERY_BYTES = 512
MAX_ROWS = 24
MAX_CELL_BYTES = 4096
MAX_RESULT_BYTES = 32768
PROJECTION = "id,title,year,synopsis,genre"
ALLOWED_TABLES = frozenset({"films", "clearance_records", "sqlite_master", "sqlite_schema"})
ALLOWED_FUNCTIONS = frozenset({"like", "count", "group_concat", "substr", "substring", "length", "lower", "upper", "sqlite_version", "coalesce", "ifnull"})


class QueryRejected(ValueError):
    """A fixed safe error; SQL, parameters and exception details stay private."""


def _authorize(action: int, arg1: str | None, arg2: str | None, database: str | None, source: str | None) -> int:
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    # SQLite emits (database=None, column='') for implicit row/count reads.
    # Attachment is independently disabled; no arbitrary database is accepted.
    if action == sqlite3.SQLITE_READ and arg1 in ALLOWED_TABLES and (database == "main" or (database is None and arg2 == "")):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in ALLOWED_FUNCTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute(path: Path, sql: str, parameters: tuple = (), *, max_vm_steps: int = 100000) -> list[dict]:
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, autocommit=True)) as reader:
            reader.row_factory = sqlite3.Row
            for option, enabled in ((sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True), (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False), (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False)):
                reader.setconfig(option, enabled)
                if reader.getconfig(option) is not enabled:
                    raise RuntimeError("SQLite runtime control unavailable")
            reader.enable_load_extension(False)
            reader.execute("PRAGMA query_only=ON")
            reader.execute("PRAGMA temp_store=MEMORY")
            for category, limit in ((sqlite3.SQLITE_LIMIT_SQL_LENGTH, 4096), (sqlite3.SQLITE_LIMIT_LENGTH, 8192), (sqlite3.SQLITE_LIMIT_COLUMN, 16), (sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 8), (sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 32), (sqlite3.SQLITE_LIMIT_ATTACHED, 0)):
                reader.setlimit(category, limit)
            deadline = time.monotonic() + 0.150
            calls = 0

            def progress() -> int:
                nonlocal calls
                calls += 1
                return int(calls * 1000 >= max_vm_steps or time.monotonic() >= deadline)

            reader.set_authorizer(_authorize)
            reader.set_progress_handler(progress, 1000)
            cursor = reader.execute(sql, parameters)
            results = []
            total = 0
            for row in cursor.fetchmany(MAX_ROWS):
                bounded = dict(row)
                for value in bounded.values():
                    if value is None:
                        continue
                    if not isinstance(value, (str, int, float)):
                        raise QueryRejected("Search could not be completed.")
                    size = len(str(value).encode("utf-8"))
                    total += size
                    if size > MAX_CELL_BYTES or total > MAX_RESULT_BYTES:
                        raise QueryRejected("Search could not be completed.")
                results.append(bounded)
            return results
    except sqlite3.Error:
        raise QueryRejected("Search could not be completed.") from None


def search(path: Path, query: str) -> list[dict]:
    if "\x00" in query or len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise QueryRejected("Search could not be completed.")
    # INTENTIONAL CWE-89: keep this sole vulnerable construction for the lab.
    # Do not reuse it for detail pages or any other application operation.
    return execute(path, f"SELECT {PROJECTION} FROM films WHERE is_public=1 AND title LIKE '%{query}%' ORDER BY id LIMIT {MAX_ROWS}")


def catalogue(path: Path) -> list[dict]:
    return execute(path, f"SELECT {PROJECTION} FROM films WHERE is_public=1 ORDER BY id")


def film(path: Path, film_id: int) -> dict | None:
    rows = execute(path, f"SELECT {PROJECTION} FROM films WHERE is_public=1 AND id=?", (film_id,))
    return rows[0] if rows else None
