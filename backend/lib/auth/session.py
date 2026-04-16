"""
Centralized user session resolution.
Single source of truth for the get_current_user FastAPI dependency.
"""

from fastapi import Header
from backend.store.auth_store import AuthDB

_db = AuthDB()


def get_current_user(authorization: str = Header(None)):
    """FastAPI dependency — resolves Bearer token to user dict or None."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    return _db.validate_session(token)
