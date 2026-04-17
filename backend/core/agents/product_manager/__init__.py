"""Product manager agent domain package."""

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


def __getattr__(name: str):
    if name in {"KatyPMAgent", "create_katy_agent"}:
        from backend.core.agents.product_manager.katy import KatyPMAgent, create_katy_agent

        return {
            "KatyPMAgent": KatyPMAgent,
            "create_katy_agent": create_katy_agent,
        }[name]
    if name in {
        "PMContext",
        "UserInsight",
        "Feature",
        "RoadmapItem",
        "Competitor",
        "ProductDecision",
        "Metric",
        "Priority",
        "Status",
    }:
        from backend.core.agents.product_manager.types import (
            Competitor,
            Feature,
            Metric,
            PMContext,
            Priority,
            ProductDecision,
            RoadmapItem,
            Status,
            UserInsight,
        )

        return {
            "PMContext": PMContext,
            "UserInsight": UserInsight,
            "Feature": Feature,
            "RoadmapItem": RoadmapItem,
            "Competitor": Competitor,
            "ProductDecision": ProductDecision,
            "Metric": Metric,
            "Priority": Priority,
            "Status": Status,
        }[name]
    raise AttributeError(f"module 'backend.core.agents.product_manager' has no attribute {name!r}")
