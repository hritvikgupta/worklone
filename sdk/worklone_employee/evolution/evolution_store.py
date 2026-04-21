"""
Evolution Store — SQLite persistence for per-employee learned skills and per-user memory.

Two tables:
  - employee_learned_skills: procedural knowledge the agent writes to itself
  - employee_user_memory:    declarative memory about a specific user across sessions
"""

import json
from typing import Optional, List
from datetime import datetime

from worklone_employee.db.database import get_connection, get_shared_db_path
from worklone_employee.workflows.utils import generate_id
from worklone_employee.logging import get_logger

logger = get_logger("evolution_store")


class EvolutionStore:
    def __init__(self, db_path: str = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_db()

    def _get_conn(self):
        return get_connection(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employee_learned_skills (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'sdk_user',
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                content TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(employee_id, owner_id, title)
            );

            CREATE TABLE IF NOT EXISTS employee_user_memory (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT,
                UNIQUE(employee_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_els_employee ON employee_learned_skills(employee_id);
            CREATE INDEX IF NOT EXISTS idx_els_employee_owner ON employee_learned_skills(employee_id, owner_id);
            CREATE INDEX IF NOT EXISTS idx_eum_employee_user ON employee_user_memory(employee_id, user_id);
        """)
        conn.commit()
        conn.close()

    # ─── Learned Skills ───

    def upsert_skill(self, employee_id: str, owner_id: str, title: str, description: str, content: str) -> dict:
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            skill_id = generate_id("lsk")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO employee_learned_skills
                    (id, employee_id, owner_id, title, description, content, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(employee_id, owner_id, title) DO UPDATE SET
                    description = excluded.description,
                    content     = excluded.content,
                    version     = employee_learned_skills.version + 1,
                    updated_at  = excluded.updated_at
                """,
                (skill_id, employee_id, owner_id, title, description, content, now, now),
            )
            row = conn.execute(
                "SELECT id, version, created_at FROM employee_learned_skills WHERE employee_id = ? AND owner_id = ? AND title = ?",
                (employee_id, owner_id, title),
            ).fetchone()
            conn.commit()
            action = "created" if row["created_at"] == now and row["version"] == 1 else "updated"
            return {"id": row["id"], "title": title, "version": row["version"], "action": action}
        finally:
            conn.close()

    def delete_skill(self, employee_id: str, owner_id: str, title: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM employee_learned_skills WHERE employee_id = ? AND owner_id = ? AND title = ?",
            (employee_id, owner_id, title),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def list_skills(self, employee_id: str, owner_id: str) -> List[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, description, version, updated_at FROM employee_learned_skills "
            "WHERE employee_id = ? AND owner_id = ? ORDER BY updated_at DESC",
            (employee_id, owner_id),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_skills_full(self, employee_id: str, owner_id: str, limit: int = 10) -> List[dict]:
        """Return full skill rows (including `content`) ordered by most recently updated."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, description, content, version, updated_at FROM employee_learned_skills "
            "WHERE employee_id = ? AND owner_id = ? ORDER BY updated_at DESC LIMIT ?",
            (employee_id, owner_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_skill(self, employee_id: str, owner_id: str, title: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM employee_learned_skills WHERE employee_id = ? AND owner_id = ? AND title = ?",
            (employee_id, owner_id, title),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    # ─── User Memory ───

    def get_user_memory(self, employee_id: str, user_id: str) -> str:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT content FROM employee_user_memory WHERE employee_id = ? AND user_id = ?",
            (employee_id, user_id),
        ).fetchone()
        conn.close()
        return row["content"] if row else ""

    def set_user_memory(self, employee_id: str, user_id: str, content: str) -> None:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO employee_user_memory (id, employee_id, user_id, content, updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(employee_id, user_id) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at",
            (generate_id("mem"), employee_id, user_id, content, now),
        )
        conn.commit()
        conn.close()
