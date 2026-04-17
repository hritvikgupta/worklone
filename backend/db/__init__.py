"""Database and persistence layer for the backend."""

from backend.db.database import ensure_shared_user_schema, get_connection, get_shared_db_path

__all__ = [
    "ensure_shared_user_schema",
    "get_connection",
    "get_shared_db_path",
]
