import sqlite3
import datetime
import uuid
from typing import List, Dict, Any, Optional
from backend.db.database import get_shared_db_path, get_connection

def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

class SprintStore:
    """SQLite storage for Sprints, Kanban Columns, Tasks, and Task Messages."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_db()

    def _init_db(self):
        with get_connection(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sprints (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    goal TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sprint_columns (
                    id TEXT PRIMARY KEY,
                    sprint_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY(sprint_id) REFERENCES sprints(id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sprint_tasks (
                    id TEXT PRIMARY KEY,
                    sprint_id TEXT NOT NULL,
                    column_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    requirements TEXT,
                    description TEXT,
                    priority TEXT DEFAULT 'medium',
                    employee_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(sprint_id) REFERENCES sprints(id) ON DELETE CASCADE,
                    FOREIGN KEY(column_id) REFERENCES sprint_columns(id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_messages (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    sender_id TEXT,
                    sender_name TEXT,
                    sender_type TEXT,
                    message_type TEXT,
                    content TEXT NOT NULL,
                    run_id TEXT,
                    created_at TEXT,
                    FOREIGN KEY(task_id) REFERENCES sprint_tasks(id) ON DELETE CASCADE
                )
            ''')
            try:
                cols = [row[1] for row in conn.execute("PRAGMA table_info(task_messages)").fetchall()]
                if "run_id" not in cols:
                    conn.execute("ALTER TABLE task_messages ADD COLUMN run_id TEXT")
            except Exception:
                pass
            # Add owner_id to sprints for per-user isolation
            try:
                sprint_cols = [row[1] for row in conn.execute("PRAGMA table_info(sprints)").fetchall()]
                if "owner_id" not in sprint_cols:
                    conn.execute("ALTER TABLE sprints ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''")
            except Exception:
                pass

            conn.execute('''
                CREATE TABLE IF NOT EXISTS sprint_runs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    employee_id TEXT,
                    employee_name TEXT,
                    status TEXT DEFAULT 'running',
                    summary TEXT,
                    error TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(task_id) REFERENCES sprint_tasks(id) ON DELETE CASCADE
                )
            ''')
            # Add completed_at to sprint_runs if missing
            try:
                conn.execute("ALTER TABLE sprint_runs ADD COLUMN completed_at TEXT")
            except Exception:
                pass

            conn.execute('''
                CREATE TABLE IF NOT EXISTS sprint_run_steps (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    title TEXT,
                    status TEXT DEFAULT 'todo',
                    order_index INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(run_id) REFERENCES sprint_runs(id) ON DELETE CASCADE
                )
            ''')

    def _seed_default_data(self, conn, owner_id: str = ""):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sprint_id = generate_id("spr")
        conn.execute(
            "INSERT INTO sprints (id, name, goal, status, owner_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sprint_id, "Sprint 1", "Initial project setup", "active", owner_id, now)
        )
        
        columns = ["To Do", "In Progress", "In Review", "Done"]
        for i, col_name in enumerate(columns):
            col_id = generate_id("col")
            conn.execute(
                "INSERT INTO sprint_columns (id, sprint_id, name, order_index, created_at) VALUES (?, ?, ?, ?, ?)",
                (col_id, sprint_id, col_name, i, now)
            )

    # --- Sprints ---
    def get_active_sprint(self, owner_id: str = "") -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            if owner_id:
                cur = conn.execute(
                    "SELECT * FROM sprints WHERE status = 'active' AND owner_id = ? ORDER BY created_at DESC LIMIT 1",
                    (owner_id,),
                )
                row = cur.fetchone()
                if not row:
                    # First access for this user — seed a personal sprint
                    self._seed_default_data(conn, owner_id)
                    conn.commit()
                    cur = conn.execute(
                        "SELECT * FROM sprints WHERE status = 'active' AND owner_id = ? ORDER BY created_at DESC LIMIT 1",
                        (owner_id,),
                    )
                    row = cur.fetchone()
            else:
                cur = conn.execute("SELECT * FROM sprints WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")
                row = cur.fetchone()
            return dict(row) if row else None

    def get_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # --- Columns ---
    def get_sprint_columns(self, sprint_id: str) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM sprint_columns WHERE sprint_id = ? ORDER BY order_index ASC", (sprint_id,))
            return [dict(row) for row in cur.fetchall()]

    # --- Tasks ---
    def get_sprint_tasks(self, sprint_id: str) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM sprint_tasks WHERE sprint_id = ? ORDER BY created_at DESC", (sprint_id,))
            return [dict(row) for row in cur.fetchall()]

    def create_task(self, sprint_id: str, column_id: str, title: str, requirements: str = "", description: str = "", priority: str = "medium", employee_id: str = "") -> str:
        task_id = generate_id("tsk")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sprint_tasks (id, sprint_id, column_id, title, requirements, description, priority, employee_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, sprint_id, column_id, title, requirements, description, priority, employee_id, now, now)
            )
        return task_id

    def update_task_details(self, task_id: str, title: str, description: str, requirements: str, priority: Optional[str] = None) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            if priority is None:
                conn.execute(
                    "UPDATE sprint_tasks SET title = ?, description = ?, requirements = ?, updated_at = ? WHERE id = ?",
                    (title, description, requirements, now, task_id)
                )
            else:
                conn.execute(
                    "UPDATE sprint_tasks SET title = ?, description = ?, requirements = ?, priority = ?, updated_at = ? WHERE id = ?",
                    (title, description, requirements, priority, now, task_id)
                )

    def update_task_column(self, task_id: str, new_column_id: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute("UPDATE sprint_tasks SET column_id = ?, updated_at = ? WHERE id = ?", (new_column_id, now, task_id))

    def update_task_assignment(self, task_id: str, employee_id: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute("UPDATE sprint_tasks SET employee_id = ?, updated_at = ? WHERE id = ?", (employee_id, now, task_id))

    # --- Messages ---
    def get_task_messages(self, task_id: str) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM task_messages WHERE task_id = ? ORDER BY created_at ASC", (task_id,))
            return [dict(row) for row in cur.fetchall()]

    def add_task_message(self, task_id: str, content: str, sender_id: str = "", sender_name: str = "", sender_type: str = "human", message_type: str = "user", run_id: str = "") -> str:
        msg_id = generate_id("msg")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO task_messages (id, task_id, sender_id, sender_name, sender_type, message_type, content, run_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (msg_id, task_id, sender_id, sender_name, sender_type, message_type, content, run_id, now)
            )
        return msg_id

    # --- Runs ---
    def create_run(self, run_id: str, task_id: str, employee_id: str = "", employee_name: str = "") -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sprint_runs (id, task_id, employee_id, employee_name, status, summary, error, created_at, updated_at) VALUES (?, ?, ?, ?, 'running', '', '', ?, ?)",
                (run_id, task_id, employee_id, employee_name, now, now)
            )

    def update_run_status(self, run_id: str, status: str, summary: str = "", error: str = "") -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed_at = now if status in ("done", "failed", "completed") else None
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE sprint_runs SET status = ?, summary = COALESCE(NULLIF(?, ''), summary), error = COALESCE(NULLIF(?, ''), error), updated_at = ?, completed_at = COALESCE(?, completed_at) WHERE id = ?",
                (status, summary, error, now, completed_at, run_id)
            )

    def list_runs_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM sprint_runs WHERE task_id = ? ORDER BY created_at DESC", (task_id,))
            runs = [dict(r) for r in cur.fetchall()]
            for run in runs:
                steps_cur = conn.execute(
                    "SELECT * FROM sprint_run_steps WHERE run_id = ? ORDER BY order_index ASC, created_at ASC",
                    (run["id"],)
                )
                run["steps"] = [dict(s) for s in steps_cur.fetchall()]
            return runs

    # --- Run Steps ---
    def upsert_run_step(self, step_id: str, run_id: str, title: str, status: str, order_index: Optional[int] = None) -> None:
        if not step_id:
            return
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            existing = conn.execute("SELECT id, order_index FROM sprint_run_steps WHERE id = ?", (step_id,)).fetchone()
            if existing:
                if order_index is None:
                    order_index = existing["order_index"]
                conn.execute(
                    "UPDATE sprint_run_steps SET title = COALESCE(NULLIF(?, ''), title), status = ?, order_index = ?, updated_at = ? WHERE id = ?",
                    (title, status, order_index, now, step_id)
                )
            else:
                if order_index is None:
                    cur = conn.execute("SELECT COALESCE(MAX(order_index), 0) AS mo FROM sprint_run_steps WHERE run_id = ?", (run_id,))
                    row = cur.fetchone()
                    order_index = (row["mo"] or 0) + 1
                conn.execute(
                    "INSERT INTO sprint_run_steps (id, run_id, title, status, order_index, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (step_id, run_id, title, status, order_index, now, now)
                )

    def update_run_step_status(self, step_id: str, status: str) -> None:
        if not step_id:
            return
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE sprint_run_steps SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, step_id)
            )
