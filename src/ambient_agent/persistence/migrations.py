"""SQLite migration / bootstrap support for the ambient agent.

Usage::

    from ambient_agent.persistence.migrations import bootstrap
    bootstrap("ambient.db")

The :func:`bootstrap` function is idempotent — it can be called every time
the application starts without risk of data loss or duplicate schema objects.

For a future multi-step migration approach, add numbered SQL files and extend
:func:`_apply_migrations` with a version-tracking table.
"""

from __future__ import annotations

import os
import sqlite3


# Path to the bundled schema SQL relative to this file.
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def bootstrap(db_path: str) -> None:
    """Create or migrate the database at *db_path*.

    Applies all CREATE TABLE IF NOT EXISTS statements and indexes from
    ``schema.sql``.  Safe to call on every startup — existing tables and
    data are preserved.

    :param db_path: Filesystem path to the SQLite database file.  The file
        (and any missing parent directories) will be created automatically.
    """
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    schema_sql = _load_schema()

    conn = sqlite3.connect(db_path)
    try:
        # Enable foreign keys and WAL mode before applying schema.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def _load_schema() -> str:
    """Return the contents of the bundled schema.sql file."""
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        return fh.read()
