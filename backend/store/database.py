"""
Shared database helpers for centralized backend persistence.
"""

import os
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "workflows.db"


def get_shared_db_path(explicit_path: str | None = None) -> str:
    """Resolve the single database file used by the backend."""
    if explicit_path:
        return str(Path(explicit_path).expanduser().resolve())

    value = os.getenv("APP_DB")
    if value:
        return str((REPO_ROOT / value).resolve()) if not os.path.isabs(value) else value

    return str(DEFAULT_DB_PATH)


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with common settings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_shared_user_schema(conn: sqlite3.Connection) -> None:
    """Ensure the shared users table supports auth and workflow use cases."""
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
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
    if "name" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''")
    if "is_active" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    if "created_at" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
