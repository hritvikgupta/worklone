"""
Workflow Engine — Agentic execution framework.
"""

from backend.core.workflows.types import (
    Workflow, Trigger, TriggerType, ExecutionResult,
    WorkflowStatus, SchedulePreset, BackgroundJob, JobStatus,
    APIKey, APIKeyType, User, WorkflowTask, WorkflowTaskStatus
)

__version__ = "4.0.0"

__all__ = [
    "Workflow", "Trigger", "TriggerType", "ExecutionResult",
    "WorkflowStatus", "SchedulePreset", "BackgroundJob", "JobStatus",
    "APIKey", "APIKeyType", "User", "WorkflowTask", "WorkflowTaskStatus",
    "WorkflowStore",
    "WorkflowExecutor",
    "CoWorkerAgent",
    "registry", "ToolRegistry",
    "BaseTool", "ToolResult",
]


def __getattr__(name):
    if name == "WorkflowStore":
        from backend.db.stores.workflow_store import WorkflowStore
        return WorkflowStore
    if name == "WorkflowExecutor":
        from backend.core.workflows.engine.executor import WorkflowExecutor
        return WorkflowExecutor
    if name == "CoWorkerAgent":
        from backend.core.workflows.engine.coworker import CoWorkerAgent
        return CoWorkerAgent
    if name in {"registry", "ToolRegistry"}:
        from backend.core.tools.system_tools.registry import registry, ToolRegistry
        return {"registry": registry, "ToolRegistry": ToolRegistry}[name]
    if name in {"BaseTool", "ToolResult"}:
        from backend.core.tools.system_tools.base import BaseTool, ToolResult
        return {"BaseTool": BaseTool, "ToolResult": ToolResult}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
