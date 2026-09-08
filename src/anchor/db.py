"""Database initialization and schema management for Anchor."""

import sqlite3
from datetime import UTC
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    seq INTEGER UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'live',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    seq INTEGER UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    text TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'live',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS anchor_fts USING fts5(
    id,
    record_type,
    title,
    category,
    content,
    reason,
    tokenize = 'porter unicode61'
);
"""


def init_database(db_path: Path, is_existing_project: bool = False) -> None:
    """Initialize SQLite database with required tables and initial metadata."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)

        # Set initial metadata if not already set
        cursor.execute("SELECT value FROM metadata WHERE key = 'version'")
        if not cursor.fetchone():
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('version', '1')")
            project_type = "existing" if is_existing_project else "new"
            bootstrap_status = "pending" if is_existing_project else "none"
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('project_type', ?)", (project_type,))
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('bootstrap_status', ?)", (bootstrap_status,)
            )
            from datetime import datetime

            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('initialized_at', ?)",
                (datetime.now(UTC).isoformat(),),
            )

        conn.commit()
