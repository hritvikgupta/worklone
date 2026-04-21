"""
Shared database helpers for SDK persistence.
"""

import os
import sqlite3
from pathlib import Path


DEFAULT_DB_DIR = Path.home() / ".worklone"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "sdk.db"


def get_shared_db_path(explicit_path: str | None = None) -> str:
    if explicit_path:
        return str(Path(explicit_path).expanduser().resolve())
    value = os.getenv("APP_DB")
    if value:
        p = Path(value)
        return str(p.resolve() if p.is_absolute() else (DEFAULT_DB_DIR / value).resolve())
    return str(DEFAULT_DB_PATH)


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_shared_user_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT DEFAULT '',
            name TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for col, defn in [
        ("email", "TEXT"),
        ("password_hash", "TEXT DEFAULT ''"),
        ("name", "TEXT DEFAULT ''"),
        ("is_active", "INTEGER DEFAULT 1"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ]:
        if col not in columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
