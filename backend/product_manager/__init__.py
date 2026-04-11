"""
Backend Product Manager Agent — Katy

An AI Product Manager agent using the ReAct pattern.
"""

from backend.product_manager.katy import KatyPMAgent, create_katy_agent
from backend.product_manager.types import (
    PMContext,
    UserInsight,
    Feature,
    RoadmapItem,
    Competitor,
    ProductDecision,
    Metric,
    Priority,
    Status,
)

__all__ = [
    "KatyPMAgent",
    "create_katy_agent",
    "PMContext",
    "UserInsight",
    "Feature",
    "RoadmapItem",
    "Competitor",
    "ProductDecision",
    "Metric",
    "Priority",
    "Status",
]

__version__ = "0.1.0"
