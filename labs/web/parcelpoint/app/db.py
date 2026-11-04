"""Request-scoped SQLite connections. All external values use parameters."""
import sqlite3
from flask import current_app, g


def get_db():
    if 'database' not in g:
        g.database = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.database.row_factory = sqlite3.Row
        g.database.execute('PRAGMA foreign_keys=ON')
    return g.database


def close_db(_error=None):
    connection = g.pop('database', None)
    if connection is not None:
        connection.close()
