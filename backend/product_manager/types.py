"""
Types and data models for Katy PM Agent.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class Priority(Enum):
    """Feature priority levels."""
    P0 = "critical"      # Must have - blocks release
    P1 = "high"          # Should have - significant value
    P2 = "medium"        # Nice to have - incremental value
    P3 = "low"           # Future consideration


class Status(Enum):
    """Feature/workflow status."""
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
    source: str  # interview, survey, support_ticket, analytics, etc.
    content: str
    category: str  # pain_point, feature_request, bug, praise, etc.
    sentiment: str  # positive, negative, neutral
    user_segment: Optional[str] = None
    priority: Priority = Priority.P2
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class Feature:
    """A product feature or user story."""
    id: str
    title: str
    description: str
    priority: Priority
    status: Status
    acceptance_criteria: List[str] = field(default_factory=list)
    user_insights: List[str] = field(default_factory=list)  # IDs of related insights
    tags: List[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None  # t-shirt size or story points
    business_value: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoadmapItem:
    """An item on the product roadmap."""
    id: str
    title: str
    description: str
    quarter: str  # Q1 2024, Q2 2024, etc.
    status: Status
    features: List[str] = field(default_factory=list)  # Feature IDs
    goals: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Competitor:
    """Competitor information for competitive analysis."""
    id: str
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    pricing: Optional[str] = None
    target_market: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProductDecision:
    """A recorded product decision (ADR style)."""
    id: str
    title: str
    context: str
    decision: str
    consequences: str
    alternatives_considered: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed, accepted, deprecated, superseded
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Metric:
    """A product metric or KPI."""
    id: str
    name: str
    description: str
    value: float
    target: Optional[float] = None
    unit: str = "count"  # count, percentage, currency, ratio
    trend: str = "stable"  # up, down, stable
    period: str = "daily"  # daily, weekly, monthly
    recorded_at: datetime = field(default_factory=datetime.now)


@dataclass
class PMContext:
    """Context maintained by Katy across sessions."""
    user_id: str
    product_name: Optional[str] = None
    product_vision: Optional[str] = None
    current_quarter: Optional[str] = None
    
    # Key data
    insights: Dict[str, UserInsight] = field(default_factory=dict)
    features: Dict[str, Feature] = field(default_factory=dict)
    roadmap: Dict[str, RoadmapItem] = field(default_factory=dict)
    competitors: Dict[str, Competitor] = field(default_factory=dict)
    decisions: Dict[str, ProductDecision] = field(default_factory=dict)
    metrics: Dict[str, Metric] = field(default_factory=dict)
    
    # Session info
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self):
        """Update the last updated timestamp."""
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
    questions: List[str] = field(default_factory=list)
    notes: str = ""
    insights: List[str] = field(default_factory=list)  # IDs of extracted insights
    recording_url: Optional[str] = None


@dataclass
class ABTest:
    """A/B test experiment."""
    id: str
    name: str
    hypothesis: str
    variant_a: str
    variant_b: str
    status: str = "draft"  # draft, running, completed, cancelled
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    primary_metric: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    winner: Optional[str] = None
