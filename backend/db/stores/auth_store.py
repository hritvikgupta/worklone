"""
Auth Database - User and OAuth integration storage
"""

import sqlite3
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime

from backend.db.database import (
    get_connection,
    get_shared_db_path,
    ensure_shared_user_schema,
)


class AuthDB:
    """SQLite database for user authentication and OAuth integrations"""

    def __init__(self, db_path: str | None = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_tables()

    def _get_conn(self):
        """Get database connection"""
        return get_connection(self.db_path)

    def _init_tables(self):
        """Initialize database tables"""
        conn = self._get_conn()
        try:
            ensure_shared_user_schema(conn)

            # Sessions table (for JWT-like tokens)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # OAuth Integrations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS integrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expires_at TIMESTAMP,
                    scopes TEXT,
                    provider_user_id TEXT,
                    provider_email TEXT,
                    metadata TEXT,
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, provider),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Chat Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    employee_id TEXT,
                    title TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Migrate: add employee_id column if missing (existing DBs)
            try:
                conn.execute("ALTER TABLE chat_sessions ADD COLUMN employee_id TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Chat Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    thinking TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
        finally:
            conn.close()

    # ─── User Methods ───────────────────────────────────────────────

    def create_user(self, email: str, password: str, name: str) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        conn = self._get_conn()
        try:
            user_id = secrets.token_urlsafe(16)
            password_hash = self._hash_password(password)

            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, email, password_hash, name, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            conn.commit()

            return self.get_user(user_id)
        except sqlite3.IntegrityError:
            return None  # Email already exists
        finally:
            conn.close()

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user by email and password"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

            if not row:
                return None

            if not self.verify_password(row["password_hash"], password):
                return None

            return dict(row)
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, email, name, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ─── Session Methods ────────────────────────────────────────────

    def create_session(self, user_id: str, expires_hours: int = 168) -> str:
        """Create a new session token (7 days default)"""
        import datetime
        conn = self._get_conn()
        try:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=expires_hours)

            conn.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, expires_at.isoformat())
            )
            conn.commit()
            return token
        finally:
            conn.close()

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user"""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT u.* FROM users u
                JOIN sessions s ON u.id = s.user_id
                WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
            """, (token,)).fetchone()

            return dict(row) if row else None
        finally:
            conn.close()

    def delete_session(self, token: str):
        """Delete session token (logout)"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()

    # ─── Integration Methods ────────────────────────────────────────

    def save_integration(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[str] = None,
        scopes: Optional[str] = None,
        provider_user_id: Optional[str] = None,
        provider_email: Optional[str] = None,
        metadata: Optional[str] = None
    ):
        """Save or update OAuth integration"""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO integrations (
                    user_id, provider, access_token, refresh_token,
                    token_expires_at, scopes, provider_user_id, provider_email, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    token_expires_at = excluded.token_expires_at,
                    scopes = excluded.scopes,
                    provider_user_id = excluded.provider_user_id,
                    provider_email = excluded.provider_email,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id, provider, access_token, refresh_token,
                token_expires_at, scopes, provider_user_id, provider_email, metadata
            ))
            conn.commit()
        finally:
            conn.close()

    def get_integration(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """Get integration by provider"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM integrations WHERE user_id = ? AND provider = ?",
                (user_id, provider)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_integrations(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all integrations for a user"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, provider, access_token, provider_email, connected_at, updated_at FROM integrations WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def disconnect_integration(self, user_id: str, provider: str):
        """Disconnect an integration"""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM integrations WHERE user_id = ? AND provider = ?",
                (user_id, provider)
            )
            conn.commit()
        finally:
            conn.close()

    # ─── Chat Session Methods ───────────────────────────────────────

    def create_chat_session(self, user_id: str, title: str = "New Chat", model: Optional[str] = None, employee_id: Optional[str] = None) -> str:
        """Create a new chat session"""
        conn = self._get_conn()
        try:
            session_id = secrets.token_urlsafe(16)
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, employee_id, title, model) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, employee_id, title, model)
            )
            conn.commit()
            return session_id
        finally:
            conn.close()

    def get_chat_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get chat session by id, optionally scoped to a user."""
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute(
                    "SELECT id, user_id, employee_id, title, model, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, user_id, employee_id, title, model, created_at, updated_at FROM chat_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_chat_sessions(self, user_id: str, limit: int = 100, employee_id: Optional[str] = "__unset__") -> list[Dict[str, Any]]:
        """List chat sessions for a user ordered by latest activity.

        employee_id filtering:
          - "__unset__" (default): return all sessions for the user
          - None: return only Katy sessions (employee_id IS NULL)
          - a string: return only sessions for that employee
        """
        conn = self._get_conn()
        try:
            if employee_id == "__unset__":
                where_clause = "WHERE s.user_id = ?"
                params = (user_id, limit)
            elif employee_id is None:
                where_clause = "WHERE s.user_id = ? AND s.employee_id IS NULL"
                params = (user_id, limit)
            else:
                where_clause = "WHERE s.user_id = ? AND s.employee_id = ?"
                params = (user_id, employee_id, limit)

            rows = conn.execute(
                f"""
                SELECT
                    s.id,
                    s.employee_id,
                    s.title,
                    s.model,
                    s.created_at,
                    s.updated_at,
                    m.content AS last_message,
                    m.role AS last_message_role,
                    m.created_at AS last_message_at
                FROM chat_sessions s
                LEFT JOIN chat_messages m
                  ON m.id = (
                      SELECT id
                      FROM chat_messages
                      WHERE session_id = s.id
                      ORDER BY id DESC
                      LIMIT 1
                  )
                {where_clause}
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_chat_session(self, session_id: str, title: Optional[str] = None, model: Optional[str] = None):
        """Update chat session metadata."""
        if title is None and model is None:
            return
        conn = self._get_conn()
        try:
            if title is not None and model is not None:
                conn.execute(
                    "UPDATE chat_sessions SET title = ?, model = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (title, model, session_id),
                )
            elif title is not None:
                conn.execute(
                    "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (title, session_id),
                )
            elif model is not None:
                conn.execute(
                    "UPDATE chat_sessions SET model = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (model, session_id),
                )
            conn.commit()
        finally:
            conn.close()

    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """Delete a chat session for a user."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def save_message(self, session_id: str, role: str, content: str, model: Optional[str] = None, thinking: Optional[str] = None):
        """Save a chat message"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, model, thinking) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, model, thinking)
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def get_chat_history(self, session_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        """Get chat history for a session"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                # Use insertion id for deterministic ordering. created_at has
                # second-level precision in SQLite and can tie for bursts.
                "SELECT id, role, content, model, thinking, created_at "
                "FROM chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ─── Utility Methods ────────────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((salt + password).encode())
        return f"{salt}${hash_obj.hexdigest()}"

    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """Verify password against stored hash"""
        salt, hash_value = stored_hash.split("$")
        hash_obj = hashlib.sha256((salt + password).encode())
        return hash_obj.hexdigest() == hash_value
