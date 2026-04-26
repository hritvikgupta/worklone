"""
Workflow Store — multi-tenant SQLite persistence.

Every record is scoped to an owner_id for user isolation.
"""

import json
import hashlib
import secrets
from typing import Optional
from datetime import datetime, timedelta
from backend.db.database import get_connection, get_shared_db_path, ensure_shared_user_schema
from backend.core.workflows.schedules.normalize import (
    cron_from_preset,
    next_run_from_cron,
    normalize_schedule_config,
)
from backend.core.workflows.types import (
    Workflow, Block, BlockConfig, BlockType, Connection,
    Trigger, TriggerType, BlockStatus, WorkflowStatus,
    ParallelGroup, ParallelType, Loop, LoopType, SchedulePreset,
    ExecutionResult, BackgroundJob, JobStatus, APIKey, APIKeyType, User
)
from backend.core.workflows.utils import generate_id
from backend.core.logging import get_logger

logger = get_logger("store")
class WorkflowStore:
    """Multi-tenant SQLite workflow storage."""
    
    def __init__(self, db_path: str = None):
        self.db_path = get_shared_db_path(db_path)
        self._init_db()
    
    def _get_conn(self):
        return get_connection(self.db_path)
    
    def _init_db(self):
        conn = self._get_conn()
        ensure_shared_user_schema(conn)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL UNIQUE,
                name TEXT DEFAULT '',
                key_type TEXT DEFAULT 'personal',
                owner_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_used_at TEXT,
                created_at TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                version INTEGER DEFAULT 1,
                owner_id TEXT NOT NULL DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_by_actor_type TEXT DEFAULT '',
                created_by_actor_id TEXT DEFAULT '',
                created_by_actor_name TEXT DEFAULT '',
                handoff_actor_type TEXT DEFAULT '',
                handoff_actor_id TEXT DEFAULT '',
                handoff_actor_name TEXT DEFAULT '',
                handoff_at TEXT,
                allowed_tools TEXT DEFAULT '[]',
                variables TEXT DEFAULT '{}',
                is_published INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            -- Legacy graph tables retained for compatibility with existing
            -- code paths and indexes.
            CREATE TABLE IF NOT EXISTS blocks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                block_type TEXT DEFAULT '',
                name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                config TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                from_block_id TEXT NOT NULL,
                to_block_id TEXT NOT NULL,
                condition TEXT DEFAULT '',
                from_handle TEXT DEFAULT '',
                to_handle TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
                FOREIGN KEY (from_block_id) REFERENCES blocks(id) ON DELETE CASCADE,
                FOREIGN KEY (to_block_id) REFERENCES blocks(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS workflow_tasks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT DEFAULT '',
                error TEXT DEFAULT '',
                task_order INTEGER DEFAULT 0,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS triggers (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                name TEXT DEFAULT '',
                config TEXT DEFAULT '{}',
                enabled INTEGER DEFAULT 1,
                webhook_path TEXT DEFAULT '',
                cron_expression TEXT DEFAULT '',
                schedule_preset TEXT DEFAULT 'hourly',
                timezone TEXT DEFAULT 'UTC',
                last_triggered_at TEXT,
                next_run_at TEXT,
                failed_count INTEGER DEFAULT 0,
                api_key TEXT DEFAULT '',
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                trigger_type TEXT DEFAULT '',
                trigger_input TEXT DEFAULT '{}',
                output TEXT DEFAULT '{}',
                error TEXT DEFAULT '',
                started_at TEXT,
                completed_at TEXT,
                block_results TEXT DEFAULT '{}',
                execution_time REAL DEFAULT 0.0,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS background_jobs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT '',
                job_type TEXT NOT NULL,
                status TEXT DEFAULT 'queued',
                payload TEXT DEFAULT '{}',
                error TEXT DEFAULT '',
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                trigger_id TEXT NOT NULL,
                path TEXT NOT NULL,
                provider TEXT DEFAULT 'generic',
                provider_config TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1,
                failed_count INTEGER DEFAULT 0,
                last_failed_at TEXT,
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS paused_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT '',
                execution_snapshot TEXT DEFAULT '{}',
                pause_points TEXT DEFAULT '[]',
                total_pause_count INTEGER DEFAULT 0,
                resumed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'paused',
                metadata TEXT DEFAULT '{}',
                paused_at TEXT,
                updated_at TEXT,
                expires_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS resume_queue (
                id TEXT PRIMARY KEY,
                paused_execution_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                context_id TEXT NOT NULL,
                resume_input TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                queued_at TEXT,
                claimed_at TEXT,
                completed_at TEXT,
                failure_reason TEXT DEFAULT '',
                FOREIGN KEY (paused_execution_id) REFERENCES paused_executions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_paused_workflow ON paused_executions(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_paused_owner ON paused_executions(owner_id);
            CREATE INDEX IF NOT EXISTS idx_paused_status ON paused_executions(status);
            CREATE INDEX IF NOT EXISTS idx_resume_paused ON resume_queue(paused_execution_id);
            CREATE INDEX IF NOT EXISTS idx_resume_status ON resume_queue(status);

            CREATE INDEX IF NOT EXISTS idx_workflows_owner ON workflows(owner_id);
            CREATE INDEX IF NOT EXISTS idx_blocks_workflow ON blocks(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_connections_workflow ON connections(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_triggers_workflow ON triggers(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_triggers_type ON triggers(trigger_type);
            CREATE INDEX IF NOT EXISTS idx_triggers_webhook ON triggers(webhook_path);
            CREATE INDEX IF NOT EXISTS idx_triggers_schedule ON triggers(cron_expression, next_run_at);
            CREATE INDEX IF NOT EXISTS idx_executions_workflow ON executions(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_executions_owner ON executions(owner_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON background_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_owner ON background_jobs(owner_id);
            CREATE INDEX IF NOT EXISTS idx_webhooks_path ON webhooks(path);
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS idx_api_keys_owner ON api_keys(owner_id);

            -- Conversation history for persistent agent memory
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tool_calls TEXT DEFAULT '[]',
                tool_call_id TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

            -- User credentials store (per-owner, dynamic)
            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(owner_id, key),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_credentials_owner ON credentials(owner_id);
            CREATE INDEX IF NOT EXISTS idx_credentials_key ON credentials(owner_id, key);

            -- User profiles for PA onboarding (permanent user context)
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL UNIQUE,
                display_name TEXT DEFAULT '',
                company_name TEXT DEFAULT '',
                role TEXT DEFAULT '',
                industry TEXT DEFAULT '',
                company_description TEXT DEFAULT '',
                expectations TEXT DEFAULT '',
                preferences TEXT DEFAULT '{}',
                onboarded INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_user_profiles_owner ON user_profiles(owner_id);
        """)
        self._ensure_column(conn, "workflows", "status", "TEXT DEFAULT 'pending'")
        self._ensure_column(conn, "workflows", "created_by_actor_type", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "created_by_actor_id", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "created_by_actor_name", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "handoff_actor_type", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "handoff_actor_id", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "handoff_actor_name", "TEXT DEFAULT ''")
        self._ensure_column(conn, "workflows", "handoff_at", "TEXT")
        self._ensure_column(conn, "workflows", "allowed_tools", "TEXT DEFAULT '[]'")
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    @staticmethod
    def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    
    # ─── User Management ───
    
    def create_user(self, user_id: str = None, name: str = "", email: str = "") -> User:
        """Create or get a user."""
        uid = user_id or generate_id("user")
        conn = self._get_conn()
        try:
            existing = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
            if existing:
                return User(
                    id=existing["id"],
                    name=existing["name"],
                    email=existing["email"],
                    is_active=bool(existing["is_active"]),
                    created_at=datetime.fromisoformat(existing["created_at"]),
                )
            
            conn.execute(
                """
                INSERT INTO users (id, name, email, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    uid,
                    name,
                    email or None,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return User(id=uid, name=name, email=email)
        finally:
            conn.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return User(
                id=row["id"],
                name=row["name"] or "",
                email=row["email"] or "",
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        finally:
            conn.close()
    
    # ─── API Key Management ───
    
    def create_api_key(
        self,
        owner_id: str,
        name: str = "",
        key_type: APIKeyType = APIKeyType.PERSONAL,
    ) -> APIKey:
        """
        Create a new API key.
        Returns APIKey with raw key (only shown once).
        """
        raw_key = f"wf_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        kid = generate_id("key")
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO api_keys (id, key_hash, name, key_type, owner_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (kid, key_hash, name, key_type.value, owner_id, datetime.now().isoformat()))
            conn.commit()
            
            return APIKey(
                id=kid,
                key_hash=key_hash,
                key_raw=raw_key,
                name=name,
                key_type=key_type,
                owner_id=owner_id,
            )
        finally:
            conn.close()
    
    def verify_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Verify an API key and return the record."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            ).fetchone()
            
            if not row:
                return None
            
            # Update last_used
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (datetime.now().isoformat(), row["id"]),
            )
            conn.commit()
            
            return APIKey(
                id=row["id"],
                key_hash=row["key_hash"],
                name=row["name"],
                key_type=APIKeyType(row["key_type"]),
                owner_id=row["owner_id"],
                is_active=bool(row["is_active"]),
                last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        finally:
            conn.close()
    
    def list_api_keys(self, owner_id: str) -> list[APIKey]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM api_keys WHERE owner_id = ? ORDER BY created_at DESC",
                (owner_id,),
            ).fetchall()
            
            return [
                APIKey(
                    id=r["id"],
                    key_hash=r["key_hash"],
                    name=r["name"],
                    key_type=APIKeyType(r["key_type"]),
                    owner_id=r["owner_id"],
                    is_active=bool(r["is_active"]),
                    last_used_at=datetime.fromisoformat(r["last_used_at"]) if r["last_used_at"] else None,
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]
        finally:
            conn.close()
    
    def revoke_api_key(self, key_id: str, owner_id: str) -> bool:
        conn = self._get_conn()
        try:
            result = conn.execute(
                "UPDATE api_keys SET is_active = 0 WHERE id = ? AND owner_id = ?",
                (key_id, owner_id),
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()
    
    # ─── Workflow CRUD ───
    
    def save_workflow(self, workflow: Workflow) -> Workflow:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO workflows 
                (id, name, description, version, owner_id, status,
                 created_by_actor_type, created_by_actor_id, created_by_actor_name,
                 handoff_actor_type, handoff_actor_id, handoff_actor_name, handoff_at,
                 allowed_tools, variables, is_published, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.id, workflow.name, workflow.description,
                workflow.version, workflow.owner_id, workflow.status.value,
                workflow.created_by_actor_type, workflow.created_by_actor_id, workflow.created_by_actor_name,
                workflow.handoff_actor_type, workflow.handoff_actor_id, workflow.handoff_actor_name,
                workflow.handoff_at.isoformat() if workflow.handoff_at else None,
                json.dumps(workflow.allowed_tools or []),
                json.dumps(workflow.variables),
                1 if workflow.is_published else 0,
                workflow.created_at.isoformat(),
                workflow.updated_at.isoformat(),
            ))
            
            # Delete existing tasks/triggers for update
            conn.execute("DELETE FROM workflow_tasks WHERE workflow_id = ?", (workflow.id,))
            conn.execute("DELETE FROM triggers WHERE workflow_id = ?", (workflow.id,))
            
            for i, task in enumerate(workflow.tasks):
                conn.execute("""
                    INSERT INTO workflow_tasks
                    (id, workflow_id, description, status, result, error, task_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.id, workflow.id, task.description, task.status.value,
                    task.result, task.error, i,
                ))
            
            for trigger in workflow.triggers:
                conn.execute("""
                    INSERT INTO triggers 
                    (id, workflow_id, trigger_type, name, config, enabled,
                     webhook_path, cron_expression, schedule_preset, timezone,
                     last_triggered_at, next_run_at, failed_count, api_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trigger.id, workflow.id, trigger.trigger_type.value,
                    trigger.name, json.dumps(trigger.config),
                    1 if trigger.enabled else 0,
                    trigger.webhook_path, trigger.cron_expression,
                    trigger.schedule_preset.value if isinstance(trigger.schedule_preset, SchedulePreset) else trigger.schedule_preset,
                    trigger.timezone,
                    trigger.last_triggered_at.isoformat() if trigger.last_triggered_at else None,
                    trigger.next_run_at.isoformat() if trigger.next_run_at else None,
                    trigger.failed_count, trigger.api_key,
                ))
            
            conn.commit()
            logger.info(f"Saved workflow: {workflow.id} ({workflow.name}) owner={workflow.owner_id}")
            return workflow
        finally:
            conn.close()
    
    def get_workflow(self, workflow_id: str, owner_id: str = None) -> Optional[Workflow]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM workflows WHERE id = ?"
            params = [workflow_id]
            if owner_id:
                query += " AND owner_id = ?"
                params.append(owner_id)
            
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            
            workflow = Workflow(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                version=row["version"],
                owner_id=row["owner_id"],
                status=WorkflowStatus(row["status"]) if row["status"] else WorkflowStatus.PENDING,
                created_by_actor_type=row["created_by_actor_type"] or "",
                created_by_actor_id=row["created_by_actor_id"] or "",
                created_by_actor_name=row["created_by_actor_name"] or "",
                handoff_actor_type=row["handoff_actor_type"] or "",
                handoff_actor_id=row["handoff_actor_id"] or "",
                handoff_actor_name=row["handoff_actor_name"] or "",
                handoff_at=datetime.fromisoformat(row["handoff_at"]) if row["handoff_at"] else None,
                allowed_tools=json.loads(row["allowed_tools"] or "[]"),
                variables=json.loads(row["variables"]),
                is_published=bool(row["is_published"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            
            # Load tasks
            from backend.core.workflows.types import WorkflowTask, WorkflowTaskStatus
            tasks = conn.execute(
                "SELECT * FROM workflow_tasks WHERE workflow_id = ? ORDER BY task_order",
                (workflow_id,),
            ).fetchall()

            for t in tasks:
                workflow.tasks.append(WorkflowTask(
                    id=t["id"],
                    description=t["description"],
                    status=WorkflowTaskStatus(t["status"]) if t["status"] else WorkflowTaskStatus.PENDING,
                    result=t["result"] or "",
                    error=t["error"] or ""
                ))
            
            # Load triggers
            for t in conn.execute(
                "SELECT * FROM triggers WHERE workflow_id = ?", (workflow_id,)
            ).fetchall():
                workflow.triggers.append(Trigger(
                    id=t["id"],
                    trigger_type=TriggerType(t["trigger_type"]),
                    name=t["name"],
                    config=json.loads(t["config"]),
                    enabled=bool(t["enabled"]),
                    webhook_path=t["webhook_path"],
                    cron_expression=t["cron_expression"],
                    schedule_preset=SchedulePreset(t["schedule_preset"]) if t["schedule_preset"] else SchedulePreset.HOURLY,
                    timezone=t["timezone"] or "UTC",
                    last_triggered_at=datetime.fromisoformat(t["last_triggered_at"]) if t["last_triggered_at"] else None,
                    next_run_at=datetime.fromisoformat(t["next_run_at"]) if t["next_run_at"] else None,
                    failed_count=t["failed_count"],
                    api_key=t["api_key"],
                ))
            
            return workflow
        finally:
            conn.close()
    
    def list_workflows(self, owner_id: str = None) -> list[Workflow]:
        conn = self._get_conn()
        try:
            if owner_id:
                rows = conn.execute(
                    "SELECT * FROM workflows WHERE owner_id = ? ORDER BY updated_at DESC",
                    (owner_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workflows ORDER BY updated_at DESC"
                ).fetchall()
            
            return [
                Workflow(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"] or "",
                    version=r["version"],
                    owner_id=r["owner_id"],
                    status=WorkflowStatus(r["status"]) if r["status"] else WorkflowStatus.PENDING,
                    created_by_actor_type=r["created_by_actor_type"] or "",
                    created_by_actor_id=r["created_by_actor_id"] or "",
                    created_by_actor_name=r["created_by_actor_name"] or "",
                    handoff_actor_type=r["handoff_actor_type"] or "",
                    handoff_actor_id=r["handoff_actor_id"] or "",
                    handoff_actor_name=r["handoff_actor_name"] or "",
                    handoff_at=datetime.fromisoformat(r["handoff_at"]) if r["handoff_at"] else None,
                    allowed_tools=json.loads(r["allowed_tools"] or "[]"),
                    variables=json.loads(r["variables"]),
                    is_published=bool(r["is_published"]),
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                )
                for r in rows
            ]
        finally:
            conn.close()
    
    def delete_workflow(self, workflow_id: str, owner_id: str = None) -> bool:
        conn = self._get_conn()
        try:
            # Guard: ensure workflow exists (and is owned by caller when owner_id is provided)
            if owner_id:
                row = conn.execute(
                    "SELECT id FROM workflows WHERE id = ? AND owner_id = ?",
                    (workflow_id, owner_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id FROM workflows WHERE id = ?",
                    (workflow_id,),
                ).fetchone()
            if not row:
                return False

            # Remove child records that do not currently use ON DELETE CASCADE.
            conn.execute("DELETE FROM executions WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM background_jobs WHERE workflow_id = ?", (workflow_id,))

            # Remove related workflow artifacts (safe even when CASCADE exists).
            conn.execute("DELETE FROM webhooks WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM triggers WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM workflow_tasks WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM paused_executions WHERE workflow_id = ?", (workflow_id,))

            if owner_id:
                result = conn.execute(
                    "DELETE FROM workflows WHERE id = ? AND owner_id = ?",
                    (workflow_id, owner_id),
                )
            else:
                result = conn.execute(
                    "DELETE FROM workflows WHERE id = ?",
                    (workflow_id,),
                )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str = "",
        user_id: str = "",
        created_by_actor_type: str = "",
        created_by_actor_id: str = "",
        created_by_actor_name: str = "",
        tasks: list[str] = None,
        allowed_tools: list[str] | None = None,
    ) -> Workflow:
        from backend.core.workflows.types import WorkflowTask, WorkflowTaskStatus
        from backend.core.workflows.utils import generate_id
        
        now = datetime.now()
        
        workflow_tasks = []
        if tasks:
            for task_desc in tasks:
                workflow_tasks.append(WorkflowTask(
                    id=generate_id("task"),
                    description=task_desc,
                    status=WorkflowTaskStatus.PENDING
                ))
                
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            owner_id=user_id,
            status=WorkflowStatus.PENDING,
            created_by_actor_type=created_by_actor_type,
            created_by_actor_id=created_by_actor_id,
            created_by_actor_name=created_by_actor_name,
            tasks=workflow_tasks,
            allowed_tools=allowed_tools or [],
            created_at=now,
            updated_at=now,
        )
        return self.save_workflow(workflow)

    def add_block(
        self,
        workflow_id: str,
        block_id: str,
        block_type: str,
        name: str,
        config: dict | None = None,
        description: str = "",
    ) -> None:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        config = config or {}
        block = Block(
            id=block_id,
            config=BlockConfig(
                block_type=BlockType(block_type),
                name=name,
                description=description,
                config=config,
                tool_name=config.get("tool_name", ""),
                model=config.get("model", ""),
                system_prompt=config.get("system_prompt", ""),
                code=config.get("code", ""),
                url=config.get("url", ""),
                method=config.get("method", "GET"),
                condition=config.get("condition", ""),
            ),
        )
        workflow.blocks.append(block)
        workflow.updated_at = datetime.now()
        self.save_workflow(workflow)

    def add_connection(
        self,
        workflow_id: str,
        from_block_id: str,
        to_block_id: str,
        connection_id: str,
        condition: str = "",
        from_handle: str = "",
        to_handle: str = "",
    ) -> None:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.connections.append(Connection(
            id=connection_id,
            from_block_id=from_block_id,
            to_block_id=to_block_id,
            condition=condition,
            from_handle=from_handle,
            to_handle=to_handle,
        ))
        workflow.updated_at = datetime.now()
        self.save_workflow(workflow)

    def add_trigger(
        self,
        workflow_id: str,
        trigger_id: str,
        trigger_type: str,
        config: dict | None = None,
    ) -> None:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        config = normalize_schedule_config(config)
        trigger = Trigger(
            id=trigger_id,
            trigger_type=TriggerType(trigger_type),
            config=config,
            cron_expression=config.get("cron", ""),
            timezone=config.get("timezone", "UTC"),
            webhook_path=config.get("webhook_path", ""),
            api_key=config.get("api_key", ""),
        )
        if trigger.trigger_type == TriggerType.SCHEDULE and trigger.cron_expression:
            trigger.next_run_at = next_run_from_cron(trigger.cron_expression)

        workflow.triggers.append(trigger)
        workflow.updated_at = datetime.now()
        self.save_workflow(workflow)

    def repair_schedule_triggers(self) -> int:
        """Backfill cron expressions for older schedule triggers created before normalization."""
        conn = self._get_conn()
        repaired = 0
        try:
            rows = conn.execute("""
                SELECT id, config, cron_expression
                FROM triggers
                WHERE trigger_type = 'schedule'
            """).fetchall()

            for row in rows:
                original_config = json.loads(row["config"]) if row["config"] else {}
                normalized_config = normalize_schedule_config(original_config)
                cron_expression = row["cron_expression"] or normalized_config.get("cron", "")

                if cron_expression == (row["cron_expression"] or "") and normalized_config == original_config:
                    continue

                conn.execute(
                    """
                    UPDATE triggers
                    SET config = ?, cron_expression = ?
                    WHERE id = ?
                    """,
                    (json.dumps(normalized_config), cron_expression, row["id"]),
                )
                repaired += 1

            if repaired:
                conn.commit()
        finally:
            conn.close()

        if repaired:
            logger.info(f"Repaired {repaired} schedule trigger(s)")
        return repaired

    def update_workflow_status(
        self,
        workflow_id: str,
        status: str,
        error: str = "",
        handoff_actor_type: str = "",
        handoff_actor_id: str = "",
        handoff_actor_name: str = "",
        handoff_at: Optional[str] = None,
    ) -> None:
        conn = self._get_conn()
        try:
            updates = ["status = ?", "updated_at = ?"]
            values: list = [status, datetime.now().isoformat()]

            if status == WorkflowStatus.ACTIVE.value:
                updates.append("is_published = 1")
            elif status in (WorkflowStatus.PAUSED.value, WorkflowStatus.CANCELLED.value):
                updates.append("is_published = 0")

            if handoff_actor_type:
                updates.append("handoff_actor_type = ?")
                values.append(handoff_actor_type)
            if handoff_actor_id:
                updates.append("handoff_actor_id = ?")
                values.append(handoff_actor_id)
            if handoff_actor_name:
                updates.append("handoff_actor_name = ?")
                values.append(handoff_actor_name)
            if handoff_actor_type or handoff_actor_id or handoff_actor_name or handoff_at:
                updates.append("handoff_at = ?")
                values.append(handoff_at or datetime.now().isoformat())

            values.append(workflow_id)
            conn.execute(
                f"UPDATE workflows SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    def list_workflows_for_user(self, owner_id: str) -> list[dict]:
        return [
            {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "status": workflow.status.value,
                "owner_id": workflow.owner_id,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "created_by_actor_type": workflow.created_by_actor_type,
                "created_by_actor_id": workflow.created_by_actor_id,
                "created_by_actor_name": workflow.created_by_actor_name,
                "handoff_actor_type": workflow.handoff_actor_type,
                "handoff_actor_id": workflow.handoff_actor_id,
                "handoff_actor_name": workflow.handoff_actor_name,
                "handoff_at": workflow.handoff_at.isoformat() if workflow.handoff_at else None,
                "allowed_tools": workflow.allowed_tools or [],
            }
            for workflow in self.list_workflows(owner_id)
        ]

    def get_workflow_executions(self, workflow_id: str, owner_id: str = None, limit: int = 50) -> list[dict]:
        return self.get_executions(workflow_id, owner_id=owner_id, limit=limit)

    def get_scheduled_workflows(self) -> list[dict]:
        self.repair_schedule_triggers()
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            rows = conn.execute("""
                SELECT DISTINCT w.*
                FROM workflows w
                JOIN triggers t ON t.workflow_id = w.id
                WHERE t.trigger_type = 'schedule'
                  AND t.enabled = 1
                  AND w.status = 'active'
                  AND (t.next_run_at IS NULL OR t.next_run_at <= ?)
                ORDER BY w.updated_at DESC
            """, (now,)).fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "user_id": row["owner_id"],
                    "owner_id": row["owner_id"],
                    "status": row["status"] or WorkflowStatus.PENDING.value,
                    "handoff_actor_type": row["handoff_actor_type"] or "",
                    "handoff_actor_id": row["handoff_actor_id"] or "",
                    "handoff_actor_name": row["handoff_actor_name"] or "",
                    "handoff_at": row["handoff_at"],
                }
                for row in rows
            ]
        finally:
            conn.close()
    
    # ─── Execution Records ───
    
    def save_execution(self, execution: ExecutionResult) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO executions
                (id, workflow_id, owner_id, status, trigger_type, trigger_input,
                 output, error, started_at, completed_at, block_results, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id, execution.workflow_id, execution.owner_id,
                execution.status.value, execution.trigger_type,
                json.dumps(execution.trigger_input),
                json.dumps(execution.output), execution.error,
                execution.started_at.isoformat(),
                execution.completed_at.isoformat() if execution.completed_at else None,
                json.dumps(execution.block_results),
                execution.execution_time,
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_executions(self, workflow_id: str, owner_id: str = None, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM executions WHERE workflow_id = ?"
            params: list = [workflow_id]
            if owner_id:
                query += " AND owner_id = ?"
                params.append(owner_id)
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": r["id"],
                    "workflow_id": r["workflow_id"],
                    "owner_id": r["owner_id"],
                    "status": r["status"],
                    "trigger_type": r["trigger_type"],
                    "trigger_input": json.loads(r["trigger_input"]) if r["trigger_input"] else {},
                    "output": json.loads(r["output"]) if r["output"] else {},
                    "error": r["error"],
                    "started_at": r["started_at"],
                    "completed_at": r["completed_at"],
                    "block_results": json.loads(r["block_results"]) if r["block_results"] else {},
                    "execution_time": r["execution_time"],
                }
                for r in rows
            ]
        finally:
            conn.close()
    
    # ─── Background Jobs ───
    
    def enqueue_job(self, job: BackgroundJob) -> BackgroundJob:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO background_jobs 
                (id, workflow_id, owner_id, job_type, status, payload, attempts, max_attempts, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.workflow_id, job.owner_id,
                job.job_type, job.status.value,
                json.dumps(job.payload), job.attempts, job.max_attempts,
                job.created_at.isoformat(),
            ))
            conn.commit()
            return job
        finally:
            conn.close()
    
    def get_pending_jobs(self, job_type: str = None, limit: int = 100) -> list[BackgroundJob]:
        """Get jobs that are queued or retrying."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM background_jobs WHERE status IN ('queued', 'retrying')"
            params: list = []
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
            query += " ORDER BY created_at ASC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [
                BackgroundJob(
                    id=r["id"],
                    workflow_id=r["workflow_id"],
                    owner_id=r["owner_id"],
                    job_type=r["job_type"],
                    status=JobStatus(r["status"]),
                    payload=json.loads(r["payload"]),
                    error=r["error"],
                    attempts=r["attempts"],
                    max_attempts=r["max_attempts"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    started_at=datetime.fromisoformat(r["started_at"]) if r["started_at"] else None,
                    completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
                )
                for r in rows
            ]
        finally:
            conn.close()
    
    def update_job_status(self, job_id: str, status: JobStatus, error: str = "", attempts: int = 0) -> None:
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            if status == JobStatus.RUNNING:
                conn.execute(
                    "UPDATE background_jobs SET status = ?, attempts = ?, started_at = ? WHERE id = ?",
                    (status.value, attempts, now, job_id),
                )
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                conn.execute(
                    "UPDATE background_jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                    (status.value, error, now, job_id),
                )
            else:
                conn.execute(
                    "UPDATE background_jobs SET status = ?, error = ?, attempts = ? WHERE id = ?",
                    (status.value, error, attempts, job_id),
                )
            conn.commit()
        finally:
            conn.close()
    
    # ─── Trigger Queries ───
    
    def get_due_schedules(self) -> list[Trigger]:
        """Get all schedule triggers that are due."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            rows = conn.execute("""
                SELECT t.*, w.id as workflow_id, w.owner_id
                FROM triggers t
                JOIN workflows w ON t.workflow_id = w.id
                WHERE t.trigger_type = 'schedule'
                  AND t.enabled = 1
                  AND (t.next_run_at IS NULL OR t.next_run_at <= ?)
            """, (now,)).fetchall()
            
            return [
                Trigger(
                    id=r["id"],
                    trigger_type=TriggerType.SCHEDULE,
                    name=r["name"],
                    config=json.loads(r["config"]),
                    enabled=bool(r["enabled"]),
                    cron_expression=r["cron_expression"],
                    schedule_preset=SchedulePreset(r["schedule_preset"]) if r["schedule_preset"] else SchedulePreset.HOURLY,
                    timezone=r["timezone"] or "UTC",
                    last_triggered_at=datetime.fromisoformat(r["last_triggered_at"]) if r["last_triggered_at"] else None,
                    next_run_at=datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None,
                    failed_count=r["failed_count"],
                )
                for r in rows
            ]
        finally:
            conn.close()
    
    def get_webhook_by_path(self, path: str) -> Optional[Trigger]:
        """Find a webhook trigger by its path."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT t.*, w.id as workflow_id, w.owner_id FROM triggers t "
                "JOIN workflows w ON t.workflow_id = w.id "
                "WHERE t.trigger_type = 'webhook' AND t.webhook_path = ? AND t.enabled = 1",
                (path,),
            ).fetchone()
            
            if not row:
                return None
            
            return Trigger(
                id=row["id"],
                trigger_type=TriggerType.WEBHOOK,
                name=row["name"],
                config=json.loads(row["config"]),
                enabled=bool(row["enabled"]),
                webhook_path=row["webhook_path"],
            )
        finally:
            conn.close()
    
    def update_schedule(self, trigger_id: str, last_triggered: datetime, next_run: datetime) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE triggers SET 
                    last_triggered_at = ?,
                    next_run_at = ?,
                    failed_count = 0
                WHERE id = ?
            """, (last_triggered.isoformat(), next_run.isoformat(), trigger_id))
            conn.commit()
        finally:
            conn.close()
    
    def increment_schedule_failure(self, trigger_id: str, error: str) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE triggers SET 
                    failed_count = failed_count + 1,
                    last_triggered_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), trigger_id))
            conn.commit()
        finally:
            conn.close()
    
    # ─── Helper Queries for Worker ───
    
    def get_workflow_by_trigger(self, trigger_id: str) -> Optional[Workflow]:
        """Get workflow that contains a trigger."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT w.* FROM workflows w
                JOIN triggers t ON w.id = t.workflow_id
                WHERE t.id = ?
            """, (trigger_id,)).fetchone()
            
            if not row:
                return None
            
            return self.get_workflow(row["id"])
        finally:
            conn.close()
    
    def get_all_schedule_triggers(self) -> list[Trigger]:
        """Get all schedule triggers."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT t.*, w.id as workflow_id, w.owner_id
                FROM triggers t
                JOIN workflows w ON t.workflow_id = w.id
                WHERE t.trigger_type = 'schedule'
            """).fetchall()

            results = []
            for r in rows:
                t = Trigger(
                    id=r["id"],
                    trigger_type=TriggerType.SCHEDULE,
                    name=r["name"],
                    config=json.loads(r["config"]),
                    enabled=bool(r["enabled"]),
                    cron_expression=r["cron_expression"],
                    schedule_preset=SchedulePreset(r["schedule_preset"]) if r["schedule_preset"] else SchedulePreset.HOURLY,
                    timezone=r["timezone"] or "UTC",
                    last_triggered_at=datetime.fromisoformat(r["last_triggered_at"]) if r["last_triggered_at"] else None,
                    next_run_at=datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None,
                    failed_count=r["failed_count"],
                )
                # Attach workflow_id as a dynamic attribute
                t.workflow_id = r["workflow_id"]  # type: ignore
                results.append(t)
            return results
        finally:
            conn.close()

    # ─── Conversation Persistence ───

    def create_conversation(self, owner_id: str, title: str = "") -> dict:
        """Create a new conversation for a user."""
        conv_id = generate_id("conv")
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO conversations (id, owner_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, owner_id, title, now, now),
            )
            conn.commit()
            return {"id": conv_id, "owner_id": owner_id, "title": title, "created_at": now}
        finally:
            conn.close()

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if not row:
                return None
            return {"id": row["id"], "owner_id": row["owner_id"], "title": row["title"],
                    "created_at": row["created_at"], "updated_at": row["updated_at"]}
        finally:
            conn.close()

    def list_conversations(self, owner_id: str, limit: int = 20) -> list[dict]:
        """List conversations for a user, most recent first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE owner_id = ? ORDER BY updated_at DESC LIMIT ?",
                (owner_id, limit),
            ).fetchall()
            return [{"id": r["id"], "owner_id": r["owner_id"], "title": r["title"],
                     "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]
        finally:
            conn.close()

    def get_latest_conversation(self, owner_id: str) -> Optional[dict]:
        """Get the most recent conversation for a user."""
        convs = self.list_conversations(owner_id, limit=1)
        return convs[0] if convs else None

    def save_message(self, conversation_id: str, role: str, content: str,
                     tool_calls: list = None, tool_call_id: str = "") -> dict:
        """Save a message to a conversation."""
        msg_id = generate_id("msg")
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_call_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id, conversation_id, role, content,
                 json.dumps(tool_calls or []), tool_call_id, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            conn.commit()
            return {"id": msg_id, "role": role, "content": content}
        finally:
            conn.close()

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[dict]:
        """Get messages for a conversation, oldest first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
            results = []
            for r in rows:
                msg = {"role": r["role"], "content": r["content"]}
                tool_calls = json.loads(r["tool_calls"])
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                if r["tool_call_id"]:
                    msg["tool_call_id"] = r["tool_call_id"]
                results.append(msg)
            return results
        finally:
            conn.close()

    # ─── Credential Store ───

    def set_credential(self, owner_id: str, key: str, value: str, description: str = "") -> dict:
        """Store or update a credential for a user."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM credentials WHERE owner_id = ? AND key = ?",
                (owner_id, key),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE credentials SET value = ?, description = ?, updated_at = ? WHERE id = ?",
                    (value, description, now, existing["id"]),
                )
                cred_id = existing["id"]
            else:
                cred_id = generate_id("cred")
                conn.execute(
                    "INSERT INTO credentials (id, owner_id, key, value, description, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cred_id, owner_id, key, value, description, now, now),
                )
            conn.commit()
            return {"id": cred_id, "key": key, "status": "saved"}
        finally:
            conn.close()

    def get_credential(self, owner_id: str, key: str) -> Optional[str]:
        """Get a credential value for a user. Returns None if not found."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT value FROM credentials WHERE owner_id = ? AND key = ?",
                (owner_id, key),
            ).fetchone()
            return row["value"] if row else None
        finally:
            conn.close()

    def list_credentials(self, owner_id: str) -> list[dict]:
        """List all credentials for a user (keys only, no values)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, key, description, created_at, updated_at FROM credentials WHERE owner_id = ?",
                (owner_id,),
            ).fetchall()
            return [{"id": r["id"], "key": r["key"], "description": r["description"],
                     "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]
        finally:
            conn.close()

    def delete_credential(self, owner_id: str, key: str) -> bool:
        """Delete a credential."""
        conn = self._get_conn()
        try:
            result = conn.execute(
                "DELETE FROM credentials WHERE owner_id = ? AND key = ?",
                (owner_id, key),
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    # ─── User Profile (PA Onboarding) ───

    def save_user_profile(self, owner_id: str, **kwargs) -> dict:
        """Create or update a user profile. Pass any profile fields as kwargs."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM user_profiles WHERE owner_id = ?", (owner_id,)
            ).fetchone()

            if existing:
                # Build dynamic UPDATE from provided kwargs
                allowed = {"display_name", "company_name", "role", "industry",
                           "company_description", "expectations", "preferences", "onboarded"}
                sets = []
                vals = []
                for k, v in kwargs.items():
                    if k in allowed:
                        sets.append(f"{k} = ?")
                        vals.append(json.dumps(v) if isinstance(v, dict) else v)
                sets.append("updated_at = ?")
                vals.append(now)
                vals.append(existing["id"])
                conn.execute(f"UPDATE user_profiles SET {', '.join(sets)} WHERE id = ?", vals)
                conn.commit()
                return self.get_user_profile(owner_id)
            else:
                pid = generate_id("prof")
                conn.execute(
                    "INSERT INTO user_profiles "
                    "(id, owner_id, display_name, company_name, role, industry, "
                    "company_description, expectations, preferences, onboarded, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (pid, owner_id,
                     kwargs.get("display_name", ""),
                     kwargs.get("company_name", ""),
                     kwargs.get("role", ""),
                     kwargs.get("industry", ""),
                     kwargs.get("company_description", ""),
                     kwargs.get("expectations", ""),
                     json.dumps(kwargs.get("preferences", {})),
                     kwargs.get("onboarded", 0),
                     now, now),
                )
                conn.commit()
                return self.get_user_profile(owner_id)
        finally:
            conn.close()

    def get_user_profile(self, owner_id: str) -> Optional[dict]:
        """Get a user's PA profile."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE owner_id = ?", (owner_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "owner_id": row["owner_id"],
                "display_name": row["display_name"],
                "company_name": row["company_name"],
                "role": row["role"],
                "industry": row["industry"],
                "company_description": row["company_description"],
                "expectations": row["expectations"],
                "preferences": json.loads(row["preferences"]) if row["preferences"] else {},
                "onboarded": bool(row["onboarded"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        finally:
            conn.close()

    def is_user_onboarded(self, owner_id: str) -> bool:
        """Check if a user has completed PA onboarding."""
        profile = self.get_user_profile(owner_id)
        return profile is not None and profile.get("onboarded", False)

    # ─── Paused Executions ───

    def save_paused_execution(
        self,
        pause_id: str,
        workflow_id: str,
        execution_id: str,
        owner_id: str,
        execution_snapshot: dict,
        pause_points: list,
        expires_minutes: int = 0,
    ) -> None:
        """Save a paused execution with its snapshot."""
        now = datetime.now()
        expires_at = None
        if expires_minutes > 0:
            expires_at = (now + timedelta(minutes=expires_minutes)).isoformat()

        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO paused_executions
                (id, workflow_id, execution_id, owner_id, execution_snapshot,
                 pause_points, total_pause_count, resumed_count, status,
                 paused_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'paused', ?, ?, ?)
            """, (
                pause_id, workflow_id, execution_id, owner_id,
                json.dumps(execution_snapshot),
                json.dumps(pause_points),
                len(pause_points),
                now.isoformat(), now.isoformat(), expires_at,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_paused_execution(self, pause_id: str, owner_id: str = None) -> Optional[dict]:
        """Get a paused execution by ID."""
        conn = self._get_conn()
        try:
            if owner_id:
                row = conn.execute(
                    "SELECT * FROM paused_executions WHERE id = ? AND owner_id = ?",
                    (pause_id, owner_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM paused_executions WHERE id = ?", (pause_id,)
                ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "execution_id": row["execution_id"],
                "owner_id": row["owner_id"],
                "execution_snapshot": json.loads(row["execution_snapshot"]) if row["execution_snapshot"] else {},
                "pause_points": json.loads(row["pause_points"]) if row["pause_points"] else [],
                "total_pause_count": row["total_pause_count"],
                "resumed_count": row["resumed_count"],
                "status": row["status"],
                "paused_at": row["paused_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
            }
        finally:
            conn.close()

    def get_paused_execution_by_execution_id(self, execution_id: str) -> Optional[dict]:
        """Get a paused execution by its execution_id."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM paused_executions WHERE execution_id = ? AND status = 'paused'",
                (execution_id,),
            ).fetchone()
            if not row:
                return None
            return self.get_paused_execution(row["id"])
        finally:
            conn.close()

    def list_paused_executions(self, owner_id: str, workflow_id: str = None, status: str = "paused") -> list[dict]:
        """List paused executions for a user."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM paused_executions WHERE owner_id = ? AND status = ?"
            params: list = [owner_id, status]
            if workflow_id:
                query += " AND workflow_id = ?"
                params.append(workflow_id)
            query += " ORDER BY paused_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": r["id"],
                    "workflow_id": r["workflow_id"],
                    "execution_id": r["execution_id"],
                    "pause_points": json.loads(r["pause_points"]) if r["pause_points"] else [],
                    "total_pause_count": r["total_pause_count"],
                    "status": r["status"],
                    "paused_at": r["paused_at"],
                    "expires_at": r["expires_at"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def update_paused_execution_status(self, pause_id: str, status: str) -> None:
        """Update paused execution status (paused, resumed, expired, cancelled)."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE paused_executions SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), pause_id),
            )
            conn.commit()
        finally:
            conn.close()

    def queue_resume(
        self, resume_id: str, paused_execution_id: str, execution_id: str,
        context_id: str, resume_input: dict = None,
    ) -> None:
        """Queue a resume request for a paused execution."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO resume_queue
                (id, paused_execution_id, execution_id, context_id, resume_input, status, queued_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (
                resume_id, paused_execution_id, execution_id,
                context_id, json.dumps(resume_input or {}),
                datetime.now().isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_pending_resumes(self, paused_execution_id: str) -> list[dict]:
        """Get pending resume requests for a paused execution."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM resume_queue WHERE paused_execution_id = ? AND status = 'pending' ORDER BY queued_at ASC",
                (paused_execution_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "paused_execution_id": r["paused_execution_id"],
                    "execution_id": r["execution_id"],
                    "context_id": r["context_id"],
                    "resume_input": json.loads(r["resume_input"]) if r["resume_input"] else {},
                    "status": r["status"],
                    "queued_at": r["queued_at"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def complete_resume(self, resume_id: str, status: str = "completed", failure_reason: str = "") -> None:
        """Mark a resume request as completed or failed."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE resume_queue SET status = ?, completed_at = ?, failure_reason = ? WHERE id = ?",
                (status, datetime.now().isoformat(), failure_reason, resume_id),
            )
            conn.commit()
        finally:
            conn.close()
