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
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DELETED = "employee_deleted"


# ─── Data Models ───

@dataclass
class Employee:
    """An AI employee (e.g. Katy the PM, Sam the Data Analyst)."""
    id: str
    name: str
    role: str = ""
    avatar_url: str = ""
    status: EmployeeStatus = EmployeeStatus.IDLE
    description: str = ""
    system_prompt: str = ""
    model: str = "openai/gpt-4o"
    owner_id: str = ""
    is_active: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
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
