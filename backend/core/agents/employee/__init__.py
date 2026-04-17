"""Employee agent domain package."""

__all__ = [
    "GenericEmployeeAgent",
    "SprintRunner",
    "TeamRunner",
]


def __getattr__(name: str):
    if name == "GenericEmployeeAgent":
        from backend.core.agents.employee.react_agent import GenericEmployeeAgent

        return GenericEmployeeAgent
    if name == "SprintRunner":
        from backend.core.agents.employee.sprint_runner import SprintRunner

        return SprintRunner
    if name == "TeamRunner":
        from backend.core.agents.employee.team_runner import TeamRunner

        return TeamRunner
    raise AttributeError(f"module 'backend.core.agents.employee' has no attribute {name!r}")
