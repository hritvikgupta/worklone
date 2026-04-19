"""
Employee types — data models for AI employees (e.g. Katy the PM, Sam the Analyst).

An Employee is a ReAct-style AI agent with a persona, system prompt, tools, skills,
and assigned tasks. This is separate from Workflows (which are run by the Harry agent).

This module also owns the employee-side product-management dataclasses used by
specialized employee PM tools so the employee package does not depend on Katy's
package for shared PM types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


# ─── Status Enums ───

class EmployeeStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SkillCategory(str, Enum):
    RESEARCH = "research"
    CODING = "coding"
    DEVOPS = "devops"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"
    PRODUCT = "product"
    DESIGN = "design"
    SALES = "sales"
    FINANCE = "finance"


class ActivityType(str, Enum):
    WORK_STARTED = "work_started"
    TASK_COMPLETED = "task_completed"
    BLOCKER_REPORTED = "blocker_reported"
    STATUS_UPDATED = "status_updated"
    TOOL_USED = "tool_used"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_COMPLETED = "workflow_completed"
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DELETED = "employee_deleted"
    COWORKER_MESSAGE_SENT = "coworker_message_sent"
    COWORKER_MESSAGE_RECEIVED = "coworker_message_received"


class MessageStatus(str, Enum):
    PENDING = "pending"
    READ = "read"
    REPLIED = "replied"


class SenderType(str, Enum):
    HUMAN = "human"
    EMPLOYEE = "employee"


class TeamTopology(str, Enum):
    SEQUENTIAL = "sequential"
    GRAPH = "graph"
    BROADCAST = "broadcast"


class TeamRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TeamMemberTaskStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


# ─── Data Models ───

@dataclass
class Employee:
    """An AI employee (e.g. Katy the PM, Sam the Data Analyst)."""
    id: str
    name: str
    role: str = ""
    avatar_url: str = ""
    cover_url: str = ""
    status: EmployeeStatus = EmployeeStatus.IDLE
    description: str = ""
    system_prompt: str = ""
    model: str = "openai/gpt-4o"
    provider: str = ""
    owner_id: str = ""
    is_active: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    memory: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmployeeTool:
    """A tool assigned to an employee."""
    id: str
    employee_id: str
    tool_name: str
    is_enabled: bool = True
    config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmployeeSkill:
    """A skill/capability of an employee."""
    id: str
    employee_id: str
    skill_name: str
    category: SkillCategory = SkillCategory.RESEARCH
    proficiency_level: int = 50  # 0-100
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PublicSkill:
    """A reusable public workplace skill stored in the shared library."""
    id: str
    slug: str
    title: str
    description: str = ""
    category: str = "general"
    employee_role: str = ""
    suggested_tools: list[str] = field(default_factory=list)
    skill_markdown: str = ""
    notes: str = ""
    source_model: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmployeeTask:
    """A task assigned to an employee."""
    id: str
    employee_id: str
    task_title: str
    task_description: str = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class EmployeeActivity:
    """An activity log entry for an employee."""
    id: str
    employee_id: str
    activity_type: ActivityType
    message: str
    task_id: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ─── Team & Inter-Employee Messaging ───

@dataclass
class TeamMessage:
    """A message in a team conversation — human or employee."""
    id: str
    conversation_id: str
    sender_type: SenderType
    sender_id: str
    sender_name: str
    content: str
    recipient_type: SenderType
    recipient_id: str
    recipient_name: str = ""
    status: MessageStatus = MessageStatus.PENDING
    reply_to: str = ""
    owner_id: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Team:
    """A team of employees that can collaborate."""
    id: str
    name: str
    goal: str = ""
    owner_id: str = ""
    topology: TeamTopology = TeamTopology.GRAPH
    project_type: str = ""
    deadline: str = ""
    sequence_order: list[str] = field(default_factory=list)
    broadcaster_id: str = ""
    attached_files: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TeamMember:
    """An employee's membership in a team."""
    id: str
    team_id: str
    employee_id: str
    employee_name: str = ""
    role_in_team: str = ""
    default_task: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TeamEdge:
    """A directed connection between two team members (who can talk to whom)."""
    id: str
    team_id: str
    from_employee_id: str
    to_employee_id: str
    trigger_condition: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TeamRun:
    """A single execution of a team working toward a goal.

    Each run gets its own conversation_id so multiple runs of the same
    team don't mix messages. Multiple runs can be active at once.
    """
    id: str
    team_id: str
    owner_id: str
    conversation_id: str
    goal: str = ""
    status: TeamRunStatus = TeamRunStatus.PENDING
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class TeamRunMember:
    """A member's participation in a specific team run with their assigned task."""
    id: str
    run_id: str
    team_id: str
    employee_id: str
    employee_name: str = ""
    employee_role: str = ""
    assigned_task: str = ""
    task_status: TeamMemberTaskStatus = TeamMemberTaskStatus.ASSIGNED
    result: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class Priority(Enum):
    """Feature priority levels for employee PM tooling."""
    P0 = "critical"
    P1 = "high"
    P2 = "medium"
    P3 = "low"


class Status(Enum):
    """Feature/workflow status for employee PM tooling."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class UserInsight:
    """A customer insight or feedback item."""
    id: str
    source: str
    content: str
    category: str
    sentiment: str
    user_segment: Optional[str] = None
    priority: Priority = Priority.P2
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)


@dataclass
class Feature:
    """A product feature or user story."""
    id: str
    title: str
    description: str
    priority: Priority
    status: Status
    acceptance_criteria: list[str] = field(default_factory=list)
    user_insights: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None
    business_value: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoadmapItem:
    """An item on the product roadmap."""
    id: str
    title: str
    description: str
    quarter: str
    status: Status
    features: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Competitor:
    """Competitor information for competitive analysis."""
    id: str
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    pricing: Optional[str] = None
    target_market: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProductDecision:
    """A recorded product decision."""
    id: str
    title: str
    context: str
    decision: str
    consequences: str
    alternatives_considered: list[str] = field(default_factory=list)
    stakeholders: list[str] = field(default_factory=list)
    status: str = "proposed"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Metric:
    """A product metric or KPI."""
    id: str
    name: str
    description: str
    value: float
    target: Optional[float] = None
    unit: str = "count"
    trend: str = "stable"
    period: str = "daily"
    recorded_at: datetime = field(default_factory=datetime.now)


@dataclass
class PMContext:
    """Context maintained by an employee acting as a PM."""
    user_id: str
    product_name: Optional[str] = None
    product_vision: Optional[str] = None
    current_quarter: Optional[str] = None
    insights: dict[str, UserInsight] = field(default_factory=dict)
    features: dict[str, Feature] = field(default_factory=dict)
    roadmap: dict[str, RoadmapItem] = field(default_factory=dict)
    competitors: dict[str, Competitor] = field(default_factory=dict)
    decisions: dict[str, ProductDecision] = field(default_factory=dict)
    metrics: dict[str, Metric] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def update_timestamp(self):
        self.last_updated = datetime.now()


@dataclass
class UserInterview:
    """User interview session data."""
    id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_segment: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    questions: list[str] = field(default_factory=list)
    notes: str = ""
    insights: list[str] = field(default_factory=list)
    recording_url: Optional[str] = None


@dataclass
class ABTest:
    """A/B test experiment."""
    id: str
    name: str
    hypothesis: str
    variant_a: str
    variant_b: str
    status: str = "draft"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    primary_metric: Optional[str] = None
    results: Optional[dict] = None
    winner: Optional[str] = None
