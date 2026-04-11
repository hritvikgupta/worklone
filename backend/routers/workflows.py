"""
Workflow Router — REST API for workflow listing and detail views.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from backend.workflows.store import WorkflowStore

router = APIRouter()
store = WorkflowStore()


def _get_owner_id(authorization: Optional[str] = Header(None)) -> str:
    if authorization and authorization.startswith("Bearer "):
        return ""
    return ""


def _format_schedule(workflow) -> str:
    if not workflow.triggers:
        return "Manual"

    trigger = workflow.triggers[0]
    if trigger.trigger_type.value == "schedule":
        if trigger.cron_expression:
            return trigger.cron_expression
        if trigger.schedule_preset:
            return str(trigger.schedule_preset.value).replace("_", " ").title()
        return "Scheduled"
    if trigger.trigger_type.value == "webhook":
        return "Webhook"
    if trigger.trigger_type.value == "api":
        return "API"
    return trigger.trigger_type.value.title()


def _workflow_owner_label(workflow) -> str:
    return workflow.handoff_actor_name or workflow.created_by_actor_name or workflow.owner_id or "Unknown"


def _workflow_to_summary(workflow) -> dict:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status.value,
        "schedule": _format_schedule(workflow),
        "owner": _workflow_owner_label(workflow),
        "owner_id": workflow.handoff_actor_id or workflow.created_by_actor_id or "",
        "owner_type": workflow.handoff_actor_type or workflow.created_by_actor_type or "",
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
        "handoff_actor_type": workflow.handoff_actor_type,
        "handoff_actor_id": workflow.handoff_actor_id,
        "handoff_actor_name": workflow.handoff_actor_name,
        "handoff_at": workflow.handoff_at.isoformat() if workflow.handoff_at else None,
        "created_by_actor_type": workflow.created_by_actor_type,
        "created_by_actor_id": workflow.created_by_actor_id,
        "created_by_actor_name": workflow.created_by_actor_name,
        "trigger_count": len(workflow.triggers),
        "block_count": len(workflow.blocks),
    }


class WorkflowListResponse(BaseModel):
    success: bool
    workflows: list[dict] = []
    error: Optional[str] = None


class WorkflowDetailResponse(BaseModel):
    success: bool
    workflow: Optional[dict] = None
    executions: list[dict] = []
    error: Optional[str] = None


@router.get("/api/workflows", response_model=WorkflowListResponse)
async def list_workflows(authorization: Optional[str] = Header(None)):
    owner_id = _get_owner_id(authorization)
    try:
        workflows = store.list_workflows(owner_id or None)
        hydrated = [store.get_workflow(workflow.id, owner_id or None) for workflow in workflows]
        result = [_workflow_to_summary(workflow) for workflow in hydrated if workflow]
        return WorkflowListResponse(success=True, workflows=result)
    except Exception as e:
        return WorkflowListResponse(success=False, error=str(e))


@router.get("/api/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(workflow_id: str, authorization: Optional[str] = Header(None)):
    owner_id = _get_owner_id(authorization)
    workflow = store.get_workflow(workflow_id, owner_id or None)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executions = store.get_workflow_executions(workflow_id, owner_id=owner_id or None, limit=20)

    workflow_data = _workflow_to_summary(workflow)
    workflow_data["variables"] = workflow.variables
    workflow_data["is_published"] = workflow.is_published
    workflow_data["connections"] = [
        {
            "id": c.id,
            "from_block_id": c.from_block_id,
            "to_block_id": c.to_block_id,
            "condition": c.condition,
            "from_handle": c.from_handle,
            "to_handle": c.to_handle,
        }
        for c in workflow.connections
    ]
    workflow_data["triggers"] = [
        {
            "id": t.id,
            "trigger_type": t.trigger_type.value,
            "name": t.name,
            "config": t.config,
            "enabled": t.enabled,
            "webhook_path": t.webhook_path,
            "cron_expression": t.cron_expression,
            "schedule_preset": t.schedule_preset.value if hasattr(t.schedule_preset, "value") else t.schedule_preset,
            "timezone": t.timezone,
            "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
            "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
            "failed_count": t.failed_count,
        }
        for t in workflow.triggers
    ]
    workflow_data["blocks"] = [
        {
            "id": b.id,
            "name": b.config.name,
            "block_type": b.config.block_type.value,
            "description": b.config.description,
            "tool_name": b.config.tool_name,
            "model": b.config.model,
            "system_prompt": b.config.system_prompt,
            "code": b.config.code,
            "url": b.config.url,
            "method": b.config.method,
            "condition": b.config.condition,
            "params": b.config.params,
            "config": b.config.config,
            "status": b.status.value,
            "error": b.error,
            "execution_time": b.execution_time,
            "inputs": b.inputs,
            "outputs": b.outputs,
        }
        for b in workflow.blocks
    ]

    return WorkflowDetailResponse(
        success=True,
        workflow=workflow_data,
        executions=executions,
    )
