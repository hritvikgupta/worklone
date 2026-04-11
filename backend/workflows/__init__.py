"""
Workflow Engine — A complete workflow automation system.

Build, execute, and monitor AI-powered workflows.
"""

from backend.workflows.types import (
    Workflow, Block, BlockConfig, BlockType, Connection,
    Trigger, TriggerType, Loop, ParallelGroup, ExecutionResult,
    WorkflowStatus, BlockStatus, ParallelType, SchedulePreset,
    BackgroundJob, JobStatus, APIKey, APIKeyType, User,
)
from backend.workflows.store import WorkflowStore
from backend.workflows.engine.executor import WorkflowExecutor
from backend.workflows.engine.dag_builder import build_dag
from backend.workflows.engine.variable_resolver import VariableResolver
from backend.workflows.tools.registry import registry, ToolRegistry
from backend.workflows.tools.base import BaseTool, ToolResult
from backend.workflows.coworker import CoWorkerAgent, create_coworker_agent

__version__ = "2.0.0"

__all__ = [
    "Workflow", "Block", "BlockConfig", "BlockType", "Connection",
    "Trigger", "TriggerType", "Loop", "ParallelGroup", "ExecutionResult",
    "WorkflowStatus", "BlockStatus", "ParallelType", "SchedulePreset",
    "BackgroundJob", "JobStatus", "APIKey", "APIKeyType", "User",
    "WorkflowStore",
    "WorkflowExecutor",
    "build_dag",
    "VariableResolver",
    "registry", "ToolRegistry",
    "BaseTool", "ToolResult",
    "CoWorkerAgent", "create_coworker_agent",
]
