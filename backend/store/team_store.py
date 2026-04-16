"""
Team Store — SQLite persistence for teams, members, edges, and inter-employee messages.

All records are scoped by owner_id for multi-tenant isolation.
Messages flow through a unified conversation table so both human<->employee
and employee<->employee messages live in one place.
"""

import json
from datetime import datetime
from typing import Optional

from backend.store.database import get_shared_db_path, get_connection
from backend.employee.types import (
    Team,
    TeamEdge,
    TeamMember,
    TeamMessage,
    TeamRun,
    TeamRunMember,
    TeamTopology,
    TeamRunStatus,
    TeamMemberTaskStatus,
    MessageStatus,
    SenderType,
)


class TeamStore:
    """SQLite storage for teams, members, edges, and inter-employee messages."""

    def __init__(self, db_path: str = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_db()

    def _get_conn(self):
        return get_connection(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                goal TEXT DEFAULT '',
                owner_id TEXT DEFAULT '',
                topology TEXT DEFAULT 'graph',
                project_type TEXT DEFAULT '',
                deadline TEXT DEFAULT '',
                sequence_order TEXT DEFAULT '[]',
                broadcaster_id TEXT DEFAULT '',
                attached_files TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                employee_name TEXT DEFAULT '',
                role_in_team TEXT DEFAULT '',
                default_task TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_edges (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                from_employee_id TEXT NOT NULL,
                to_employee_id TEXT NOT NULL,
                trigger_condition TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_type TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT DEFAULT '',
                content TEXT NOT NULL,
                recipient_type TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                recipient_name TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                reply_to TEXT DEFAULT '',
                owner_id TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS team_runs (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                owner_id TEXT DEFAULT '',
                conversation_id TEXT NOT NULL,
                goal TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_run_members (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                employee_name TEXT DEFAULT '',
                employee_role TEXT DEFAULT '',
                assigned_task TEXT DEFAULT '',
                task_status TEXT DEFAULT 'assigned',
                result TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (run_id) REFERENCES team_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_session_memory (
                run_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                author_id TEXT DEFAULT '',
                author_name TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                PRIMARY KEY (run_id, key),
                FOREIGN KEY (run_id) REFERENCES team_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_teams_owner_id ON teams(owner_id);
            CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
            CREATE INDEX IF NOT EXISTS idx_team_members_employee_id ON team_members(employee_id);
            CREATE INDEX IF NOT EXISTS idx_team_edges_team_id ON team_edges(team_id);
            CREATE INDEX IF NOT EXISTS idx_team_messages_conversation_id ON team_messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_team_messages_recipient ON team_messages(recipient_id, status);
            CREATE INDEX IF NOT EXISTS idx_team_messages_sender ON team_messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_team_messages_reply_to ON team_messages(reply_to);
            CREATE INDEX IF NOT EXISTS idx_team_runs_team_id ON team_runs(team_id);
            CREATE INDEX IF NOT EXISTS idx_team_runs_owner_id ON team_runs(owner_id);
            CREATE INDEX IF NOT EXISTS idx_team_runs_status ON team_runs(status);
            CREATE INDEX IF NOT EXISTS idx_team_run_members_run_id ON team_run_members(run_id);
            CREATE INDEX IF NOT EXISTS idx_team_run_members_employee_id ON team_run_members(employee_id);
            CREATE INDEX IF NOT EXISTS idx_team_session_memory_run_id ON team_session_memory(run_id);
        """)
        
        # Apply schema migrations for existing tables
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN project_type TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN deadline TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN sequence_order TEXT DEFAULT '[]'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN broadcaster_id TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN attached_files TEXT DEFAULT '[]'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE team_members ADD COLUMN default_task TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE team_run_members ADD COLUMN completed_at TEXT")
        except Exception:
            pass

        conn.commit()
        conn.close()

    # ─── Team CRUD ───

    def create_team(self, team: Team) -> Team:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO teams (id, name, goal, owner_id, topology, project_type, deadline, sequence_order, broadcaster_id, attached_files, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                team.id, team.name, team.goal, team.owner_id,
                team.topology.value, team.project_type, team.deadline,
                json.dumps(team.sequence_order), team.broadcaster_id,
                json.dumps(team.attached_files),
                team.created_at.isoformat(), team.updated_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return team

    def update_team(self, team: Team) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            """UPDATE teams 
               SET name = ?, goal = ?, topology = ?, project_type = ?, deadline = ?, sequence_order = ?, broadcaster_id = ?, attached_files = ?, updated_at = ?
               WHERE id = ? AND owner_id = ?""",
            (
                team.name, team.goal, team.topology.value, team.project_type, team.deadline,
                json.dumps(team.sequence_order), team.broadcaster_id,
                json.dumps(team.attached_files),
                team.updated_at.isoformat(),
                team.id, team.owner_id
            ),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_team(self, team_id: str, owner_id: str = "") -> Optional[Team]:
        conn = self._get_conn()
        if owner_id:
            row = conn.execute(
                "SELECT * FROM teams WHERE id = ? AND owner_id = ?",
                (team_id, owner_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM teams WHERE id = ?", (team_id,)
            ).fetchone()
        conn.close()
        return self._row_to_team(row) if row else None

    def list_teams(self, owner_id: str) -> list[Team]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM teams WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_team(r) for r in rows if r]

    def delete_team(self, team_id: str, owner_id: str = "") -> bool:
        conn = self._get_conn()
        if owner_id:
            cursor = conn.execute(
                "DELETE FROM teams WHERE id = ? AND owner_id = ?",
                (team_id, owner_id),
            )
        else:
            cursor = conn.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Team Members ───

    def add_member(self, member: TeamMember) -> TeamMember:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO team_members
               (id, team_id, employee_id, employee_name, role_in_team, default_task, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                member.id, member.team_id, member.employee_id,
                member.employee_name, member.role_in_team, member.default_task,
                member.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return member

    def list_members(self, team_id: str) -> list[TeamMember]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM team_members WHERE team_id = ? ORDER BY created_at",
            (team_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_member(r) for r in rows if r]

    def remove_member(self, member_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM team_members WHERE id = ?", (member_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def clear_team_members(self, team_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_employee_teams(self, employee_id: str) -> list[dict]:
        """Return teams an employee belongs to along with their teammates."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT t.*, tm.role_in_team
               FROM teams t
               JOIN team_members tm ON t.id = tm.team_id
               WHERE tm.employee_id = ?
               ORDER BY t.created_at DESC""",
            (employee_id,),
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            team = self._row_to_team(r)
            if team:
                members = self.list_members(team.id)
                results.append({"team": team, "members": members})
        return results

    # ─── Team Edges ───

    def add_edge(self, edge: TeamEdge) -> TeamEdge:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO team_edges
               (id, team_id, from_employee_id, to_employee_id, trigger_condition, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                edge.id, edge.team_id, edge.from_employee_id,
                edge.to_employee_id, edge.trigger_condition,
                edge.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return edge

    def list_edges(self, team_id: str) -> list[TeamEdge]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM team_edges WHERE team_id = ? ORDER BY created_at",
            (team_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_edge(r) for r in rows if r]

    def remove_edge(self, edge_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM team_edges WHERE id = ?", (edge_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def clear_team_edges(self, team_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM team_edges WHERE team_id = ?", (team_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Messages ───

    def send_message(self, msg: TeamMessage) -> TeamMessage:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO team_messages
               (id, conversation_id, sender_type, sender_id, sender_name,
                content, recipient_type, recipient_id, recipient_name,
                status, reply_to, owner_id, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.id, msg.conversation_id, msg.sender_type.value,
                msg.sender_id, msg.sender_name, msg.content,
                msg.recipient_type.value, msg.recipient_id, msg.recipient_name,
                msg.status.value, msg.reply_to, msg.owner_id,
                json.dumps(msg.metadata), msg.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return msg

    def get_message(self, message_id: str) -> Optional[TeamMessage]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM team_messages WHERE id = ?", (message_id,)
        ).fetchone()
        conn.close()
        return self._row_to_message(row) if row else None

    def get_unread_messages(self, recipient_id: str, recipient_type: str = "employee") -> list[TeamMessage]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM team_messages
               WHERE recipient_id = ? AND recipient_type = ? AND status = 'pending'
               ORDER BY created_at ASC""",
            (recipient_id, recipient_type),
        ).fetchall()
        conn.close()
        return [self._row_to_message(r) for r in rows if r]

    def mark_read(self, message_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE team_messages SET status = 'read' WHERE id = ? AND status = 'pending'",
            (message_id,),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def mark_replied(self, message_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE team_messages SET status = 'replied' WHERE id = ?",
            (message_id,),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_replies(self, message_id: str) -> list[TeamMessage]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM team_messages WHERE reply_to = ? ORDER BY created_at ASC",
            (message_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_message(r) for r in rows if r]

    def get_conversation(self, conversation_id: str, limit: int = 50) -> list[TeamMessage]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM team_messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (conversation_id, limit),
        ).fetchall()
        conn.close()
        return [self._row_to_message(r) for r in rows if r]

    def get_messages_between(
        self, employee_a: str, employee_b: str, limit: int = 20
    ) -> list[TeamMessage]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM team_messages
               WHERE (sender_id = ? AND recipient_id = ?)
                  OR (sender_id = ? AND recipient_id = ?)
               ORDER BY created_at DESC
               LIMIT ?""",
            (employee_a, employee_b, employee_b, employee_a, limit),
        ).fetchall()
        conn.close()
        return list(reversed([self._row_to_message(r) for r in rows if r]))

    # ─── Team Runs ───

    def create_run(self, run: TeamRun) -> TeamRun:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO team_runs
               (id, team_id, owner_id, conversation_id, goal, status, metadata,
                created_at, updated_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.id, run.team_id, run.owner_id, run.conversation_id,
                run.goal, run.status.value, json.dumps(run.metadata),
                run.created_at.isoformat(), run.updated_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
            ),
        )
        conn.commit()
        conn.close()
        return run

    def get_run(self, run_id: str) -> Optional[TeamRun]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM team_runs WHERE id = ?", (run_id,)
        ).fetchone()
        conn.close()
        return self._row_to_run(row) if row else None

    def list_runs(self, team_id: str, owner_id: str = "") -> list[TeamRun]:
        conn = self._get_conn()
        if owner_id:
            rows = conn.execute(
                "SELECT * FROM team_runs WHERE team_id = ? AND owner_id = ? ORDER BY created_at DESC",
                (team_id, owner_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM team_runs WHERE team_id = ? ORDER BY created_at DESC",
                (team_id,),
            ).fetchall()
        conn.close()
        return [self._row_to_run(r) for r in rows if r]

    def update_run_status(self, run_id: str, status: TeamRunStatus) -> bool:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        completed_at = now if status in (TeamRunStatus.COMPLETED, TeamRunStatus.FAILED) else None
        cursor = conn.execute(
            "UPDATE team_runs SET status = ?, updated_at = ?, completed_at = ? WHERE id = ?",
            (status.value, now, completed_at, run_id),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Team Run Members ───

    def add_run_member(self, member: TeamRunMember) -> TeamRunMember:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO team_run_members
               (id, run_id, team_id, employee_id, employee_name, employee_role,
                assigned_task, task_status, result, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                member.id, member.run_id, member.team_id, member.employee_id,
                member.employee_name, member.employee_role, member.assigned_task,
                member.task_status.value, member.result,
                member.created_at.isoformat(), member.updated_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return member

    def get_run_member(self, run_id: str, employee_id: str) -> Optional[TeamRunMember]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM team_run_members WHERE run_id = ? AND employee_id = ?",
            (run_id, employee_id),
        ).fetchone()
        conn.close()
        return self._row_to_run_member(row) if row else None

    def list_run_members(self, run_id: str) -> list[TeamRunMember]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM team_run_members WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_run_member(r) for r in rows if r]

    def update_run_member(
        self, run_id: str, employee_id: str,
        task_status: TeamMemberTaskStatus = None, result: str = None
    ) -> bool:
        fields, values = [], []
        if task_status is not None:
            fields.append("task_status = ?")
            values.append(task_status.value)
            # Set completed_at when task reaches a terminal status
            if task_status in (TeamMemberTaskStatus.DONE, TeamMemberTaskStatus.BLOCKED):
                fields.append("completed_at = ?")
                values.append(datetime.now().isoformat())
        if result is not None:
            fields.append("result = ?")
            values.append(result)
        if not fields:
            return False
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.extend([run_id, employee_id])
        conn = self._get_conn()
        cursor = conn.execute(
            f"UPDATE team_run_members SET {', '.join(fields)} WHERE run_id = ? AND employee_id = ?",
            values,
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_full_run(self, run_id: str) -> Optional[dict]:
        """Return a run with its members — everything needed to describe an active team run."""
        run = self.get_run(run_id)
        if not run:
            return None
        members = self.list_run_members(run_id)
        return {"run": run, "members": members}

    # ─── Team Session Memory (shared scratchpad per run) ───

    MAX_SESSION_VALUE_BYTES = 16 * 1024  # 16 KB per key

    def session_memory_write(
        self,
        run_id: str,
        key: str,
        value: str,
        author_id: str = "",
        author_name: str = "",
    ) -> tuple[bool, str]:
        """Insert or update a key in the team session scratchpad.

        Returns (success, error_message).
        """
        if not key or not key.strip():
            return False, "key must be non-empty"
        key = key.strip()[:200]
        if value is None:
            value = ""
        encoded_len = len(value.encode("utf-8"))
        if encoded_len > self.MAX_SESSION_VALUE_BYTES:
            return False, (
                f"value too large ({encoded_len} bytes). "
                f"Limit per key is {self.MAX_SESSION_VALUE_BYTES} bytes. "
                f"Split into multiple keys or summarize."
            )
        now = datetime.now().isoformat()
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT created_at FROM team_session_memory WHERE run_id = ? AND key = ?",
            (run_id, key),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE team_session_memory
                   SET value = ?, author_id = ?, author_name = ?, updated_at = ?
                   WHERE run_id = ? AND key = ?""",
                (value, author_id, author_name, now, run_id, key),
            )
        else:
            conn.execute(
                """INSERT INTO team_session_memory
                   (run_id, key, value, author_id, author_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, key, value, author_id, author_name, now, now),
            )
        conn.commit()
        conn.close()
        return True, ""

    def session_memory_read(self, run_id: str, key: str) -> Optional[dict]:
        """Read a single key. Returns None if missing."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM team_session_memory WHERE run_id = ? AND key = ?",
            (run_id, key.strip()),
        ).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "key": row["key"],
            "value": row["value"],
            "author_id": row["author_id"],
            "author_name": row["author_name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def session_memory_list(self, run_id: str) -> list[dict]:
        """List all keys for a run, sorted by updated_at desc."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM team_session_memory
               WHERE run_id = ?
               ORDER BY updated_at DESC""",
            (run_id,),
        ).fetchall()
        conn.close()
        return [
            {
                "key": r["key"],
                "value": r["value"],
                "author_id": r["author_id"],
                "author_name": r["author_name"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def session_memory_delete(self, run_id: str, key: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM team_session_memory WHERE run_id = ? AND key = ?",
            (run_id, key.strip()),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ─── Cross-run history (for a given team) ───

    def list_recent_completed_runs(
        self, team_id: str, limit: int = 3, exclude_run_id: str = ""
    ) -> list[dict]:
        """Return the most recent completed runs for a team with their members.

        Used to give new runs context about what the team accomplished previously.
        """
        conn = self._get_conn()
        if exclude_run_id:
            rows = conn.execute(
                """SELECT * FROM team_runs
                   WHERE team_id = ? AND status = 'completed' AND id != ?
                   ORDER BY completed_at DESC, created_at DESC
                   LIMIT ?""",
                (team_id, exclude_run_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM team_runs
                   WHERE team_id = ? AND status = 'completed'
                   ORDER BY completed_at DESC, created_at DESC
                   LIMIT ?""",
                (team_id, limit),
            ).fetchall()
        runs = [self._row_to_run(r) for r in rows if r]
        conn.close()
        out = []
        for run in runs:
            if not run:
                continue
            members = self.list_run_members(run.id)
            out.append({"run": run, "members": members})
        return out

    # ─── Row Converters ───

    @staticmethod
    def _row_to_team(row) -> Optional[Team]:
        if not row:
            return None
        try:
            topology = TeamTopology(row["topology"])
        except ValueError:
            topology = TeamTopology.GRAPH
        try:
            sequence_order = json.loads(row["sequence_order"]) if "sequence_order" in row.keys() and row["sequence_order"] else []
        except (json.JSONDecodeError, TypeError):
            sequence_order = []
        try:
            attached_files = json.loads(row["attached_files"]) if "attached_files" in row.keys() and row["attached_files"] else []
        except (json.JSONDecodeError, TypeError):
            attached_files = []
        return Team(
            id=row["id"],
            name=row["name"],
            goal=row["goal"],
            owner_id=row["owner_id"],
            topology=topology,
            project_type=row["project_type"] if "project_type" in row.keys() else "",
            deadline=row["deadline"] if "deadline" in row.keys() else "",
            sequence_order=sequence_order,
            broadcaster_id=row["broadcaster_id"] if "broadcaster_id" in row.keys() else "",
            attached_files=attached_files,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_member(row) -> Optional[TeamMember]:
        if not row:
            return None
        return TeamMember(
            id=row["id"],
            team_id=row["team_id"],
            employee_id=row["employee_id"],
            employee_name=row["employee_name"],
            role_in_team=row["role_in_team"],
            default_task=row["default_task"] if "default_task" in row.keys() else "",
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_edge(row) -> Optional[TeamEdge]:
        if not row:
            return None
        return TeamEdge(
            id=row["id"],
            team_id=row["team_id"],
            from_employee_id=row["from_employee_id"],
            to_employee_id=row["to_employee_id"],
            trigger_condition=row["trigger_condition"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_message(row) -> Optional[TeamMessage]:
        if not row:
            return None
        try:
            sender_type = SenderType(row["sender_type"])
        except ValueError:
            sender_type = SenderType.EMPLOYEE
        try:
            recipient_type = SenderType(row["recipient_type"])
        except ValueError:
            recipient_type = SenderType.EMPLOYEE
        try:
            status = MessageStatus(row["status"])
        except ValueError:
            status = MessageStatus.PENDING
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return TeamMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            sender_type=sender_type,
            sender_id=row["sender_id"],
            sender_name=row["sender_name"],
            content=row["content"],
            recipient_type=recipient_type,
            recipient_id=row["recipient_id"],
            recipient_name=row["recipient_name"],
            status=status,
            reply_to=row["reply_to"],
            owner_id=row["owner_id"],
            metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_run(row) -> Optional[TeamRun]:
        if not row:
            return None
        try:
            status = TeamRunStatus(row["status"])
        except ValueError:
            status = TeamRunStatus.PENDING
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return TeamRun(
            id=row["id"],
            team_id=row["team_id"],
            owner_id=row["owner_id"],
            conversation_id=row["conversation_id"],
            goal=row["goal"],
            status=status,
            metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    @staticmethod
    def _row_to_run_member(row) -> Optional[TeamRunMember]:
        if not row:
            return None
        try:
            task_status = TeamMemberTaskStatus(row["task_status"])
        except ValueError:
            task_status = TeamMemberTaskStatus.ASSIGNED
        return TeamRunMember(
            id=row["id"],
            run_id=row["run_id"],
            team_id=row["team_id"],
            employee_id=row["employee_id"],
            employee_name=row["employee_name"],
            employee_role=row["employee_role"],
            assigned_task=row["assigned_task"],
            task_status=task_status,
            result=row["result"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
