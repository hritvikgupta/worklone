"""
Employee Store — SQLite persistence for AI employees.
"""

import json
from typing import Optional, List
from datetime import datetime

from worklone_employee.db.database import get_connection, get_shared_db_path
from worklone_employee.types import (
    Employee, EmployeeTool, EmployeeSkill, PublicSkill, EmployeeTask, EmployeeActivity,
    EmployeeStatus, TaskStatus, TaskPriority, SkillCategory, ActivityType
)
from worklone_employee.workflows.utils import generate_id
from worklone_employee.logging.logger import get_logger

logger = get_logger("employee_store")


class EmployeeStore:
    """SQLite storage for employees, their tools, skills, tasks, and activity."""

    def __init__(self, db_path: str = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_db()

    def _get_conn(self):
        return get_connection(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT DEFAULT '',
                avatar_url TEXT DEFAULT '',
                cover_url TEXT DEFAULT '',
                status TEXT DEFAULT 'idle',
                description TEXT DEFAULT '',
                system_prompt TEXT DEFAULT '',
                model TEXT DEFAULT 'openai/gpt-4o',
                owner_id TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                temperature REAL DEFAULT 0.7,
                max_tokens INTEGER DEFAULT 4096,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        conn.commit()

        for col_def in [
            ("memory", "TEXT DEFAULT '[]'"),
            ("provider", "TEXT DEFAULT ''"),
            ("cover_url", "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE employees ADD COLUMN {col_def[0]} {col_def[1]}")
                conn.commit()
            except Exception:
                pass

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employee_tools (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                config TEXT DEFAULT '{}',
                created_at TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employee_skills (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                category TEXT DEFAULT 'research',
                proficiency_level INTEGER DEFAULT 50,
                description TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS public_skills (
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'general',
                employee_role TEXT DEFAULT '',
                suggested_tools TEXT DEFAULT '[]',
                skill_markdown TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                source_model TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS employee_tasks (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                task_title TEXT NOT NULL,
                task_description TEXT DEFAULT '',
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employee_activity_log (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                message TEXT NOT NULL,
                task_id TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                timestamp TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_employees_owner_id ON employees(owner_id);
            CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
            CREATE INDEX IF NOT EXISTS idx_employee_tools_employee_id ON employee_tools(employee_id);
            CREATE INDEX IF NOT EXISTS idx_employee_skills_employee_id ON employee_skills(employee_id);
            CREATE INDEX IF NOT EXISTS idx_public_skills_slug ON public_skills(slug);
            CREATE INDEX IF NOT EXISTS idx_public_skills_category ON public_skills(category);
            CREATE INDEX IF NOT EXISTS idx_employee_tasks_employee_id ON employee_tasks(employee_id);
            CREATE INDEX IF NOT EXISTS idx_employee_tasks_status ON employee_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_employee_activity_employee_id ON employee_activity_log(employee_id);

            CREATE TABLE IF NOT EXISTS employee_usage_log (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                model TEXT DEFAULT '',
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0,
                timestamp TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_employee_usage_employee_id ON employee_usage_log(employee_id);
            CREATE INDEX IF NOT EXISTS idx_employee_usage_timestamp ON employee_usage_log(timestamp);

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                employee_id TEXT,
                title TEXT DEFAULT 'New Chat',
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                thinking TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_employee ON chat_sessions(employee_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
        """)
        conn.commit()
        conn.close()

    # ─── Chat Sessions ───

    def create_chat_session(self, user_id: str, employee_id: str = "", title: str = "New Chat", model: str = "") -> str:
        import secrets
        session_id = secrets.token_urlsafe(16)
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chat_sessions (id, user_id, employee_id, title, model) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, employee_id, title, model),
        )
        conn.commit()
        conn.close()
        return session_id

    def get_chat_session(self, session_id: str, user_id: str = "") -> Optional[dict]:
        conn = self._get_conn()
        if user_id:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id)
            ).fetchone()
        else:
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_chat_sessions(self, user_id: str, employee_id: str = "") -> list:
        conn = self._get_conn()
        if employee_id:
            rows = conn.execute(
                "SELECT * FROM chat_sessions WHERE user_id = ? AND employee_id = ? ORDER BY updated_at DESC",
                (user_id, employee_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_chat_session(self, session_id: str, title: str = "", model: str = "") -> None:
        conn = self._get_conn()
        if title and model:
            conn.execute("UPDATE chat_sessions SET title=?, model=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (title, model, session_id))
        elif title:
            conn.execute("UPDATE chat_sessions SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (title, session_id))
        elif model:
            conn.execute("UPDATE chat_sessions SET model=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (model, session_id))
        conn.commit()
        conn.close()

    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def save_message(self, session_id: str, role: str, content: str, model: str = "", thinking: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, model, thinking) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, model or "", thinking or ""),
        )
        conn.execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        conn.commit()
        conn.close()

    def get_chat_history(self, session_id: str, limit: int = 500) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, role, content, model, thinking, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ─── Employee CRUD ───

    def create_employee(self, employee: Employee) -> Employee:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employees (id, name, role, avatar_url, cover_url, status, description,
                                   system_prompt, model, provider, owner_id, is_active,
                                   temperature, max_tokens, memory, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee.id, employee.name, employee.role, employee.avatar_url, employee.cover_url,
            employee.status.value, employee.description, employee.system_prompt,
            employee.model, employee.provider, employee.owner_id, int(employee.is_active),
            employee.temperature, employee.max_tokens,
            json.dumps(employee.memory),
            employee.created_at.isoformat(), employee.updated_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return employee

    def get_employee(self, employee_id: str, owner_id: str = "") -> Optional[Employee]:
        conn = self._get_conn()
        if owner_id:
            row = conn.execute(
                "SELECT * FROM employees WHERE id = ? AND owner_id = ?",
                (employee_id, owner_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM employees WHERE id = ?",
                (employee_id,)
            ).fetchone()
        conn.close()
        return self._row_to_employee(row) if row else None

    def list_employees(self, owner_id: str = "") -> List[Employee]:
        conn = self._get_conn()
        if owner_id:
            rows = conn.execute(
                "SELECT * FROM employees WHERE owner_id = ? ORDER BY created_at DESC",
                (owner_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM employees ORDER BY created_at DESC").fetchall()
        conn.close()
        return [self._row_to_employee(r) for r in rows if r]

    def update_employee(self, employee_id: str, updates: dict, owner_id: str = "") -> Optional[Employee]:
        existing = self.get_employee(employee_id, owner_id)
        if not existing:
            return None

        fields = []
        values = []
        for key, value in updates.items():
            if key in ("name", "role", "avatar_url", "cover_url", "description",
                       "system_prompt", "model", "provider", "status", "temperature",
                       "max_tokens", "is_active", "memory"):
                fields.append(f"{key} = ?")
                if key == "is_active":
                    values.append(int(value))
                elif key == "status":
                    values.append(value.value if hasattr(value, 'value') else value)
                elif key == "memory":
                    values.append(json.dumps(value) if isinstance(value, list) else value)
                else:
                    values.append(value)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(employee_id)
        if owner_id:
            values.append(owner_id)

        owner_clause = "AND owner_id = ?" if owner_id else ""
        conn = self._get_conn()
        conn.execute(
            f"UPDATE employees SET {', '.join(fields)} WHERE id = ? {owner_clause}",
            values
        )
        conn.commit()
        conn.close()
        return self.get_employee(employee_id, owner_id)

    def delete_employee(self, employee_id: str, owner_id: str = "") -> bool:
        conn = self._get_conn()
        if owner_id:
            cursor = conn.execute(
                "DELETE FROM employees WHERE id = ? AND owner_id = ?",
                (employee_id, owner_id)
            )
        else:
            cursor = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Employee Tools ───

    def add_tool_to_employee(self, tool: EmployeeTool) -> EmployeeTool:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employee_tools (id, employee_id, tool_name, is_enabled, config, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tool.id, tool.employee_id, tool.tool_name,
            int(tool.is_enabled), json.dumps(tool.config),
            tool.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return tool

    def get_employee_tools(self, employee_id: str, owner_id: str = "") -> List[EmployeeTool]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM employee_tools WHERE employee_id = ?",
            (employee_id,)
        ).fetchall()
        conn.close()
        return [self._row_to_tool(r) for r in rows if r]

    def remove_tool_from_employee(self, employee_id: str, tool_id: str, owner_id: str = "") -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM employee_tools WHERE id = ? AND employee_id = ?",
            (tool_id, employee_id)
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def update_employee_tool(self, employee_id: str, tool_id: str, updates: dict,
                              owner_id: str = "") -> Optional[EmployeeTool]:
        fields = []
        values = []
        for key, value in updates.items():
            if key in ("is_enabled", "config"):
                fields.append(f"{key} = ?")
                values.append(int(value) if key == "is_enabled" else json.dumps(value) if isinstance(value, dict) else value)

        if not fields:
            return None

        values.extend([tool_id, employee_id])
        conn = self._get_conn()
        conn.execute(
            f"UPDATE employee_tools SET {', '.join(fields)} WHERE id = ? AND employee_id = ?",
            values
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM employee_tools WHERE id = ? AND employee_id = ?",
            (tool_id, employee_id)
        ).fetchone()
        conn.close()
        return self._row_to_tool(row) if row else None

    # ─── Employee Skills ───

    def add_skill_to_employee(self, skill: EmployeeSkill) -> EmployeeSkill:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employee_skills (id, employee_id, skill_name, category,
                                         proficiency_level, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            skill.id, skill.employee_id, skill.skill_name,
            skill.category.value if hasattr(skill.category, 'value') else skill.category,
            skill.proficiency_level, skill.description,
            skill.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return skill

    def get_employee_skills(self, employee_id: str, owner_id: str = "") -> List[EmployeeSkill]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM employee_skills WHERE employee_id = ?",
            (employee_id,)
        ).fetchall()
        conn.close()
        return [self._row_to_skill(r) for r in rows if r]

    def remove_skill_from_employee(self, employee_id: str, skill_id: str, owner_id: str = "") -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM employee_skills WHERE id = ? AND employee_id = ?",
            (skill_id, employee_id)
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Public Skills Library ───

    def save_public_skill(self, skill: PublicSkill) -> PublicSkill:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO public_skills (
                id, slug, title, description, category, employee_role,
                suggested_tools, skill_markdown, notes, source_model,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                category = excluded.category,
                employee_role = excluded.employee_role,
                suggested_tools = excluded.suggested_tools,
                skill_markdown = excluded.skill_markdown,
                notes = excluded.notes,
                source_model = excluded.source_model,
                updated_at = excluded.updated_at
        """, (
            skill.id, skill.slug, skill.title, skill.description, skill.category,
            skill.employee_role, json.dumps(skill.suggested_tools), skill.skill_markdown,
            skill.notes, skill.source_model,
            skill.created_at.isoformat(), skill.updated_at.isoformat(),
        ))
        conn.commit()
        conn.close()
        return skill

    def list_public_skills(self) -> List[PublicSkill]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM public_skills ORDER BY category ASC, title ASC").fetchall()
        conn.close()
        return [self._row_to_public_skill(r) for r in rows if r]

    def get_public_skill(self, slug: str) -> Optional[PublicSkill]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM public_skills WHERE slug = ?", (slug,)).fetchone()
        conn.close()
        return self._row_to_public_skill(row) if row else None

    # ─── Employee Tasks ───

    def create_task(self, task: EmployeeTask) -> EmployeeTask:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employee_tasks (id, employee_id, task_title, task_description,
                                        status, priority, tags, metadata,
                                        created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.employee_id, task.task_title, task.task_description,
            task.status.value if hasattr(task.status, 'value') else task.status,
            task.priority.value if hasattr(task.priority, 'value') else task.priority,
            json.dumps(task.tags), json.dumps(task.metadata),
            task.created_at.isoformat(), task.updated_at.isoformat(),
            task.completed_at.isoformat() if task.completed_at else None
        ))
        conn.commit()
        conn.close()
        return task

    def get_employee_tasks(self, employee_id: str, owner_id: str = "") -> List[EmployeeTask]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM employee_tasks WHERE employee_id = ? ORDER BY created_at DESC",
            (employee_id,)
        ).fetchall()
        conn.close()
        return [self._row_to_task(r) for r in rows if r]

    def update_task(self, employee_id: str, task_id: str, updates: dict,
                    owner_id: str = "") -> Optional[EmployeeTask]:
        fields = []
        values = []
        for key, value in updates.items():
            if key in ("task_title", "task_description", "status", "priority", "tags", "metadata"):
                fields.append(f"{key} = ?")
                if key in ("tags", "metadata") and isinstance(value, (dict, list)):
                    values.append(json.dumps(value))
                elif key in ("status", "priority") and hasattr(value, 'value'):
                    values.append(value.value)
                else:
                    values.append(value)

        if not fields:
            return None

        fields.append("updated_at = ?")
        values.extend([datetime.now().isoformat(), task_id, employee_id])
        conn = self._get_conn()
        conn.execute(
            f"UPDATE employee_tasks SET {', '.join(fields)} WHERE id = ? AND employee_id = ?",
            values
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM employee_tasks WHERE id = ? AND employee_id = ?",
            (task_id, employee_id)
        ).fetchone()
        conn.close()
        return self._row_to_task(row) if row else None

    def delete_task(self, employee_id: str, task_id: str, owner_id: str = "") -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM employee_tasks WHERE id = ? AND employee_id = ?",
            (task_id, employee_id)
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Activity Log ───

    def log_activity(self, activity: EmployeeActivity) -> EmployeeActivity:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employee_activity_log (id, employee_id, activity_type, message,
                                               task_id, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            activity.id, activity.employee_id,
            activity.activity_type.value if hasattr(activity.activity_type, 'value') else activity.activity_type,
            activity.message, activity.task_id,
            json.dumps(activity.metadata),
            activity.timestamp.isoformat()
        ))
        conn.commit()
        conn.close()
        return activity

    def get_employee_activity(self, employee_id: str, owner_id: str = "", limit: int = 50) -> List[EmployeeActivity]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM employee_activity_log WHERE employee_id = ? ORDER BY timestamp DESC LIMIT ?",
            (employee_id, limit)
        ).fetchall()
        conn.close()
        return [self._row_to_activity(r) for r in rows if r]

    # ─── Usage Log ───

    def log_usage(self, employee_id: str, model: str, input_tokens: int, output_tokens: int,
                  total_tokens: int, cost: float, duration_ms: int) -> None:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO employee_usage_log (id, employee_id, model, input_tokens, output_tokens,
                                            total_tokens, cost, duration_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_id("usg"), employee_id, model, input_tokens, output_tokens,
            total_tokens, cost, duration_ms, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_usage_stats(self, owner_id: str = "") -> dict:
        conn = self._get_conn()
        if owner_id:
            row = conn.execute("""
                SELECT COALESCE(SUM(u.total_tokens), 0) as total_tokens,
                       COALESCE(SUM(u.cost), 0) as total_cost,
                       COALESCE(SUM(u.duration_ms), 0) as total_duration_ms,
                       COUNT(*) as total_calls
                FROM employee_usage_log u
                WHERE u.employee_id IN (SELECT id FROM employees WHERE owner_id = ?)
            """, (owner_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(cost), 0) as total_cost,
                       COALESCE(SUM(duration_ms), 0) as total_duration_ms,
                       COUNT(*) as total_calls
                FROM employee_usage_log
            """).fetchone()
        conn.close()
        return dict(row) if row else {}

    def get_usage_by_employee(self, owner_id: str = "") -> list:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT e.id, e.name, e.role, e.model, e.avatar_url,
                   COALESCE(SUM(u.input_tokens), 0) as input_tokens,
                   COALESCE(SUM(u.output_tokens), 0) as output_tokens,
                   COALESCE(SUM(u.total_tokens), 0) as total_tokens,
                   COALESCE(SUM(u.cost), 0) as total_cost,
                   COALESCE(SUM(u.duration_ms), 0) as total_duration_ms,
                   COUNT(u.id) as total_calls
            FROM employees e
            LEFT JOIN employee_usage_log u ON e.id = u.employee_id
            WHERE e.owner_id = ? OR ? = ''
            GROUP BY e.id
            ORDER BY total_tokens DESC
        """, (owner_id, owner_id)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ─── Bulk ───

    def get_employee_full(self, employee_id: str, owner_id: str = "") -> Optional[dict]:
        employee = self.get_employee(employee_id, owner_id)
        if not employee:
            return None
        return {
            "employee": employee,
            "tools": self.get_employee_tools(employee_id),
            "skills": self.get_employee_skills(employee_id),
            "tasks": self.get_employee_tasks(employee_id),
            "activity": self.get_employee_activity(employee_id, limit=20),
        }

    # ─── Row converters ───

    @staticmethod
    def _row_to_employee(row) -> Optional[Employee]:
        if not row:
            return None
        try:
            status = EmployeeStatus(row["status"])
        except ValueError:
            status = EmployeeStatus.IDLE
        memory = []
        try:
            if "memory" in row.keys():
                raw = row["memory"]
                memory = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except (json.JSONDecodeError, TypeError):
            memory = []
        return Employee(
            id=row["id"], name=row["name"], role=row["role"],
            avatar_url=row["avatar_url"],
            cover_url=row["cover_url"] if "cover_url" in row.keys() else "",
            status=status, description=row["description"],
            system_prompt=row["system_prompt"], model=row["model"],
            provider=row["provider"] if "provider" in row.keys() else "",
            owner_id=row["owner_id"], is_active=bool(row["is_active"]),
            temperature=row["temperature"], max_tokens=row["max_tokens"],
            memory=memory,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_tool(row) -> Optional[EmployeeTool]:
        if not row:
            return None
        try:
            config = json.loads(row["config"]) if row["config"] else {}
        except (json.JSONDecodeError, TypeError):
            config = {}
        return EmployeeTool(
            id=row["id"], employee_id=row["employee_id"], tool_name=row["tool_name"],
            is_enabled=bool(row["is_enabled"]), config=config,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_skill(row) -> Optional[EmployeeSkill]:
        if not row:
            return None
        try:
            category = SkillCategory(row["category"])
        except ValueError:
            category = SkillCategory.RESEARCH
        return EmployeeSkill(
            id=row["id"], employee_id=row["employee_id"], skill_name=row["skill_name"],
            category=category, proficiency_level=row["proficiency_level"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_public_skill(row) -> Optional[PublicSkill]:
        if not row:
            return None
        try:
            suggested_tools = json.loads(row["suggested_tools"]) if row["suggested_tools"] else []
        except (json.JSONDecodeError, TypeError):
            suggested_tools = []
        return PublicSkill(
            id=row["id"], slug=row["slug"], title=row["title"],
            description=row["description"], category=row["category"] or "general",
            employee_role=row["employee_role"] or "",
            suggested_tools=suggested_tools, skill_markdown=row["skill_markdown"] or "",
            notes=row["notes"] or "", source_model=row["source_model"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_task(row) -> Optional[EmployeeTask]:
        if not row:
            return None
        try:
            status = TaskStatus(row["status"])
        except ValueError:
            status = TaskStatus.TODO
        try:
            priority = TaskPriority(row["priority"])
        except ValueError:
            priority = TaskPriority.MEDIUM
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        completed_at = None
        if row["completed_at"]:
            try:
                completed_at = datetime.fromisoformat(row["completed_at"])
            except (ValueError, TypeError):
                completed_at = None
        return EmployeeTask(
            id=row["id"], employee_id=row["employee_id"],
            task_title=row["task_title"], task_description=row["task_description"],
            status=status, priority=priority, tags=tags, metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=completed_at,
        )

    @staticmethod
    def _row_to_activity(row) -> Optional[EmployeeActivity]:
        if not row:
            return None
        try:
            activity_type = ActivityType(row["activity_type"])
        except ValueError:
            activity_type = ActivityType.STATUS_UPDATED
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return EmployeeActivity(
            id=row["id"], employee_id=row["employee_id"],
            activity_type=activity_type, message=row["message"],
            task_id=row["task_id"], metadata=metadata,
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
