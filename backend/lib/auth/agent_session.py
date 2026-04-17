"""
Centralized agent/chat session resolution.
Handles per-user per-employee chat sessions.
"""

from typing import Optional
from backend.db.stores.auth_store import AuthDB

_db = AuthDB()


def create_agent_session(user_id: str, employee_id: Optional[str] = None, title: str = "New Chat", model: Optional[str] = None) -> str:
    return _db.create_chat_session(user_id, title=title, model=model, employee_id=employee_id)


def get_agent_session(session_id: str, user_id: Optional[str] = None):
    return _db.get_chat_session(session_id, user_id=user_id)


def list_agent_sessions(user_id: str, employee_id: Optional[str] = "__unset__", limit: int = 100):
    return _db.list_chat_sessions(user_id, limit=limit, employee_id=employee_id)


def update_agent_session(session_id: str, title: Optional[str] = None, model: Optional[str] = None):
    return _db.update_chat_session(session_id, title=title, model=model)


def delete_agent_session(session_id: str, user_id: str) -> bool:
    return _db.delete_chat_session(session_id, user_id)


def save_agent_message(session_id: str, role: str, content: str, model: Optional[str] = None, thinking: Optional[str] = None):
    return _db.save_message(session_id, role, content, model=model, thinking=thinking)


def get_agent_history(session_id: str, limit: int = 50):
    return _db.get_chat_history(session_id, limit=limit)
