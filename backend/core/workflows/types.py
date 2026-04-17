"""
Core types for the workflow engine — v2 with full Sim-like features.

Includes: triggers, parallel execution, multi-tenant auth, background jobs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


# ─── Block Types ───

class BlockType(str, Enum):
    START = "start"
    AGENT = "agent"
    FUNCTION = "function"
    CONDITION = "condition"
    HTTP = "http"
    RESPONSE = "response"
    TOOL = "tool"
    LOOP = "loop"
    PARALLEL = "parallel"
    WAIT = "wait"
    VARIABLE = "variable"
    TRIGGER = "trigger"
    HUMAN_APPROVAL = "human_approval"
    END = "end"


class LoopType(str, Enum):
    FOR = "for"
    FOR_EACH = "foreach"
    WHILE = "while"


class ParallelType(str, Enum):
    COUNT = "count"
    COLLECTION = "collection"


# ─── Trigger Types ───

class TriggerType(str, Enum):
    API = "api"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    MANUAL = "manual"


class SchedulePreset(str, Enum):
    EVERY_MINUTE = "every_minute"
    EVERY_5_MIN = "every_5_min"
    EVERY_15_MIN = "every_15_min"
    EVERY_30_MIN = "every_30_min"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


# ─── Status Enums ───

class WorkflowStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class BlockStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# ─── Auth ───

class APIKeyType(str, Enum):
    PERSONAL = "personal"
    WORKSPACE = "workspace"


# ─── Data Models ───

@dataclass
class BlockConfig:
    """Configuration for a single block."""
    block_type: BlockType
    name: str
    description: str = ""
    params: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    tool_name: str = ""
    model: str = ""
    system_prompt: str = ""
    code: str = ""
    url: str = ""
    method: str = "GET"
    condition: str = ""
    loop_type: LoopType = LoopType.FOR_EACH
    loop_value: str = ""
    parallel_count: int = 1
    parallel_type: ParallelType = ParallelType.COLLECTION
    parallel_distribution: str = ""  # JSON array of items to distribute


@dataclass
class Block:
    """A single block in a workflow."""
    id: str
    config: BlockConfig
    position: dict = field(default_factory=lambda: {"x": 0, "y": 0})
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    status: BlockStatus = BlockStatus.PENDING
    error: str = ""
    execution_time: float = 0.0
    result: Any = None


@dataclass
class Connection:
    """A connection between two blocks."""
    id: str
    from_block_id: str
    to_block_id: str
    condition: str = ""
    from_handle: str = ""  # For parallel: which handle the edge comes from
    to_handle: str = ""


@dataclass
class Loop:
    id: str
    block_ids: list[str] = field(default_factory=list)
    loop_type: LoopType = LoopType.FOR_EACH
    iterations: int = 0
    loop_value: str = ""


@dataclass
class ParallelGroup:
    """A parallel execution group (like Sim's SerializedParallel)."""
    id: str
    block_ids: list[str] = field(default_factory=list)
    parallel_type: ParallelType = ParallelType.COLLECTION
    count: int = 1  # For 'count' type
    distribution: list = field(default_factory=list)  # For 'collection' type


@dataclass
class Trigger:
    """A trigger that starts a workflow."""
    id: str
    trigger_type: TriggerType
    name: str = ""
    config: dict = field(default_factory=dict)
    enabled: bool = True
    webhook_path: str = ""  # For WEBHOOK: the URL path segment
    cron_expression: str = ""  # For SCHEDULE
    schedule_preset: SchedulePreset = SchedulePreset.HOURLY
    timezone: str = "UTC"
    last_triggered_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    failed_count: int = 0
    api_key: str = ""  # For API triggers


class WorkflowTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowTask:
    id: str
    description: str
    status: WorkflowTaskStatus = WorkflowTaskStatus.PENDING
    result: str = ""
    error: str = ""

@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str = ""
    version: int = 1
    owner_id: str = ""  # Multi-tenant: which user owns this
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_by_actor_type: str = ""
    created_by_actor_id: str = ""
    created_by_actor_name: str = ""
    handoff_actor_type: str = ""
    handoff_actor_id: str = ""
    handoff_actor_name: str = ""
    handoff_at: Optional[datetime] = None
    tasks: list[WorkflowTask] = field(default_factory=list)
    triggers: list[Trigger] = field(default_factory=list)
    variables: dict = field(default_factory=dict)
    is_published: bool = False  # Only published workflows can be triggered
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    """Result of a workflow execution."""
    execution_id: str
    workflow_id: str
    owner_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    trigger_type: str = ""  # What started this: api, webhook, schedule, manual
    trigger_input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    error: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    block_results: dict = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class BackgroundJob:
    """A background job (async execution)."""
    id: str
    workflow_id: str
    owner_id: str = ""
    job_type: str = ""  # workflow_execution, schedule_dispatch
    status: JobStatus = JobStatus.QUEUED
    payload: dict = field(default_factory=dict)
    error: str = ""
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class APIKey:
    """An API key for authentication."""
    id: str
    key_hash: str  # Hashed version stored in DB
    key_raw: str = ""  # Only available at creation time
    name: str = ""
    key_type: APIKeyType = APIKeyType.PERSONAL
    owner_id: str = ""
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class User:
    """A user in the system."""
    id: str
    name: str = ""
    email: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolConfig:
    """Configuration for a tool."""
    name: str
    description: str
    schema: dict = field(default_factory=dict)
    auth_type: str = "none"
    method: str = "GET"
    url: str = ""
    headers: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    transform_response: str = ""
    direct_execution: bool = False


@dataclass
class LLMProviderConfig:
    name: str
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class KnowledgeBase:
    id: str
    name: str
    description: str = ""
    owner_id: str = ""
    documents: list[dict] = field(default_factory=list)
    embedding_model: str = ""
    chunk_size: int = 500
    chunk_overlap: int = 50
