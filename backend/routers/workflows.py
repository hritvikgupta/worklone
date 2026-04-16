"""
Workflow Router — REST API for workflow listing and detail views.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.store.workflow_store import WorkflowStore
from backend.lib.auth.session import get_current_user
from backend.workflows.engine.executor import WorkflowExecutor
from backend.workflows.types import ExecutionResult, WorkflowStatus
from backend.workflows.utils import generate_id

router = APIRouter()
store = WorkflowStore()
executor = WorkflowExecutor(store)


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
            expr = trigger.cron_expression
            if expr == "0 0 * * *":
                return "Daily at midnight"
            if expr == "0 * * * *":
                return "Hourly"
            if expr == "*/15 * * * *":
                return "Every 15 minutes"
            if expr == "0 9 * * 1-5":
                return "Weekdays at 9 AM"
            if expr == "0 0 * * 0":
                return "Weekly on Sunday"
            return expr
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
                "handoff_at": (
            workflow.triggers[0].next_run_at.isoformat() 
            if getattr(workflow, "triggers", None) and len(workflow.triggers) > 0 and workflow.triggers[0].next_run_at 
            else (workflow.handoff_at.isoformat() if workflow.handoff_at else None)
        ),
        "created_by_actor_type": workflow.created_by_actor_type,
        "created_by_actor_id": workflow.created_by_actor_id,
        "created_by_actor_name": workflow.created_by_actor_name,
        "trigger_count": len(workflow.triggers),
        "task_count": len(workflow.tasks) if hasattr(workflow, "tasks") else 0,
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


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(authorization: Optional[str] = Header(None)):
    owner_id = _get_owner_id(authorization)
    try:
        workflows = store.list_workflows(owner_id or None)
        hydrated = [store.get_workflow(workflow.id, owner_id or None) for workflow in workflows]
        result = [_workflow_to_summary(workflow) for workflow in hydrated if workflow]
        return WorkflowListResponse(success=True, workflows=result)
    except Exception as e:
        return WorkflowListResponse(success=False, error=str(e))


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(workflow_id: str, authorization: Optional[str] = Header(None)):
    owner_id = _get_owner_id(authorization)
    workflow = store.get_workflow(workflow_id, owner_id or None)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executions = store.get_workflow_executions(workflow_id, owner_id=owner_id or None, limit=20)

    workflow_data = _workflow_to_summary(workflow)
    workflow_data["variables"] = workflow.variables
    workflow_data["is_published"] = workflow.is_published
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
    workflow_data["tasks"] = [
        {
            "id": t.id,
            "description": t.description,
            "status": t.status.value,
            "result": t.result,
            "error": t.error,
        }
        for t in workflow.tasks
    ]

    return WorkflowDetailResponse(
        success=True,
        workflow=workflow_data,
        executions=executions,
    )


# ─── Pause / Resume Endpoints ───


class ResumeRequest(BaseModel):
    input: dict = {}


@router.get("/workflows/{workflow_id}/paused")
async def list_paused_executions(workflow_id: str, user=Depends(get_current_user)):
    """List paused executions for a workflow."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    paused = store.list_paused_executions(owner_id=user["id"], workflow_id=workflow_id)
    return {"success": True, "paused": paused}


@router.get("/workflows/paused/all")
async def list_all_paused(user=Depends(get_current_user)):
    """List all paused executions for the current user."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    paused = store.list_paused_executions(owner_id=user["id"])
    return {"success": True, "paused": paused}


@router.get("/workflows/paused/{pause_id}")
async def get_paused_detail(pause_id: str, user=Depends(get_current_user)):
    """Get full details of a paused execution including snapshot."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    paused = store.get_paused_execution(pause_id, owner_id=user["id"])
    if not paused:
        raise HTTPException(status_code=404, detail="Paused execution not found")
    return {"success": True, "paused": paused}


@router.post("/workflows/paused/{pause_id}/resume")
async def resume_workflow(pause_id: str, request: ResumeRequest, user=Depends(get_current_user)):
    """Resume a paused workflow with optional input."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        result = await executor.resume_execution(
            pause_id=pause_id,
            resume_input=request.input,
            owner_id=user["id"],
        )
        return {
            "success": True,
            "execution_id": result.execution_id,
            "status": result.status.value,
            "output": result.output,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workflows/paused/{pause_id}/cancel")
async def cancel_paused(pause_id: str, user=Depends(get_current_user)):
    """Cancel a paused execution."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    paused = store.get_paused_execution(pause_id, owner_id=user["id"])
    if not paused:
        raise HTTPException(status_code=404, detail="Paused execution not found")
    store.update_paused_execution_status(pause_id, "cancelled")
    store.update_workflow_status(paused["workflow_id"], "active")
    return {"success": True}

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "qwen/qwen3-max-thinking"
    timezone: str = "UTC"
    current_time: str = ""

@router.post("/workflows/generate")
async def generate_workflow(request: GenerateRequest, user=Depends(get_current_user)):
    """Generate a workflow from a natural language prompt."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    from backend.tools.run_tools.llm_tool import LLMTool
    from backend.workflows.utils import generate_id
    import json
    
    llm = LLMTool()
    
    sys_prompt = f"""
    You are an expert workflow architect. Parse the user's prompt into a JSON workflow definition.
    The user's current timezone is {request.timezone} and their current time is {request.current_time}.
    If the user asks for a specific time of day (e.g. "every morning at 9am"), you MUST construct the cron schedule 
    relative to {request.timezone}, taking into account the current time context if needed.
    
    Return ONLY valid JSON matching this structure:
    {{
        "name": "Short descriptive name",
        "description": "Clear description of what it does",
        "schedule": "cron expression if requested, or null",
        "tasks": [
            "Step 1 natural language description",
            "Step 2 natural language description"
        ]
    }}
    """
    
    response = await llm.execute({
        "prompt": request.prompt,
        "system_prompt": sys_prompt,
        "model": request.model,
        "response_format": {"type": "json_object"}
    })
    
    if not response.success:
        raise HTTPException(status_code=500, detail="Failed to generate workflow")
        
    try:
        content_text = response.data.get("content", "{}")
        # Strip markdown formatting like ```json ... ```
        content_text = content_text.strip()
        if content_text.startswith("```json"):
            content_text = content_text[7:]
        if content_text.startswith("```"):
            content_text = content_text[3:]
        if content_text.endswith("```"):
            content_text = content_text[:-3]
            
        wf_data = json.loads(content_text.strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")
        
    workflow_id = generate_id("wf")
    
    # Store workflow
    workflow = store.create_workflow(
        workflow_id=workflow_id,
        name=wf_data.get("name", "Generated Workflow"),
        description=wf_data.get("description", ""),
        user_id=user["id"],
        tasks=wf_data.get("tasks", [])
    )
    
    # Add schedule trigger if parsed
    if wf_data.get("schedule"):
        store.add_trigger(
            workflow_id=workflow_id,
            trigger_id=generate_id("trig"),
            trigger_type="schedule",
            config={
                "cron_expression": wf_data["schedule"],
                "timezone": request.timezone,
            }
        )
        # Set handoff_at to the calculated next_run_at
        from backend.workflows.schedules.normalize import next_run_from_cron
        next_run = next_run_from_cron(wf_data["schedule"])
        if next_run:
            wf = store.get_workflow(workflow_id)
            if wf:
                wf.handoff_at = next_run
                store.save_workflow(wf)

    return {"success": True, "workflow_id": workflow_id}

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, user=Depends(get_current_user)):
    """Execute a workflow manually — streams SSE events live like the employee chat."""
    from fastapi.responses import StreamingResponse
    from backend.workflows.engine.coworker import CoWorkerAgent
    import json as _json

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    workflow = store.get_workflow(workflow_id, user["id"])
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executor._cleanup_stale_executions(workflow_id, user["id"])

    exec_id = generate_id("exec")
    exec_result = ExecutionResult(
        execution_id=exec_id,
        workflow_id=workflow_id,
        owner_id=user["id"],
        status=WorkflowStatus.RUNNING,
        trigger_type="manual",
        trigger_input={},
        started_at=datetime.now(),
    )
    store.save_execution(exec_result)
    store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING.value)

    async def event_generator():
        agent = CoWorkerAgent(owner_id=user["id"])
        success = True
        try:
            async for event in agent.execute_workflow(
                workflow_id, trigger_input={}, stream=True, emit_events=True
            ):
                if isinstance(event, dict):
                    yield f"data: {_json.dumps(event)}\n\n"
                    if event.get("type") == "error":
                        success = False
                        exec_result.error = event.get("message", "")
                else:
                    yield f"data: {_json.dumps({'type': 'content', 'token': str(event)})}\n\n"
        except Exception as e:
            success = False
            exec_result.error = str(e)
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        now = datetime.now()
        exec_result.completed_at = now
        exec_result.execution_time = (now - exec_result.started_at).total_seconds()

        final_wf = store.get_workflow(workflow_id) or store.get_workflow(workflow_id, user["id"])
        if final_wf:
            if success and final_wf.status != WorkflowStatus.FAILED:
                final_wf.status = WorkflowStatus.ACTIVE
                exec_result.status = WorkflowStatus.COMPLETED
                exec_result.output = {"message": "Workflow completed successfully"}
                # Ensure tasks are marked completed
                for t in final_wf.tasks:
                    if t.status.value == "running":
                        t.status = WorkflowTaskStatus.COMPLETED
                        if not t.result:
                            t.result = "Completed."
            else:
                final_wf.status = WorkflowStatus.FAILED
                exec_result.status = WorkflowStatus.FAILED
                for t in final_wf.tasks:
                    if t.status.value == "running":
                        t.status = WorkflowTaskStatus.FAILED
            store.save_workflow(final_wf)

        store.save_execution(exec_result)
        yield f"data: {_json.dumps({'type': 'done', 'execution_id': exec_id, 'status': exec_result.status.value})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

class UpdateWorkflowRequest(BaseModel):
    schedule: Optional[str] = None
    timezone: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tasks: Optional[list[dict]] = None  # [{"id": "...", "description": "...", "status": "..."}]

@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: UpdateWorkflowRequest, user=Depends(get_current_user)):
    """Update a workflow's details or tasks."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from backend.workflows.types import Trigger, TriggerType, SchedulePreset, WorkflowStatus
    from backend.workflows.schedules.normalize import next_run_from_cron
    from backend.workflows.utils import generate_id as gen_id

    workflow = store.get_workflow(workflow_id, user["id"])
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description

    if request.status is not None:
        try:
            workflow.status = WorkflowStatus(request.status)
            # If toggled off, also disable the trigger so worker skips it
            if workflow.triggers:
                trigger = workflow.triggers[0]
                trigger.enabled = (workflow.status == WorkflowStatus.ACTIVE)
                
                # If enabling, recalculate next run
                if trigger.enabled and trigger.cron_expression:
                    trigger.next_run_at = next_run_from_cron(trigger.cron_expression)
                    workflow.handoff_at = trigger.next_run_at
        except ValueError:
            pass

    if request.schedule is not None:
        tz = request.timezone or "UTC"
        cron_expr = request.schedule
        next_run = next_run_from_cron(cron_expr)

        if workflow.triggers:
            trigger = workflow.triggers[0]
            trigger.cron_expression = cron_expr
            trigger.timezone = tz
            trigger.schedule_preset = SchedulePreset.CUSTOM
            trigger.next_run_at = next_run
            trigger.enabled = True
        else:
            workflow.triggers.append(Trigger(
                id=gen_id("trig"),
                trigger_type=TriggerType.SCHEDULE,
                name="Schedule",
                cron_expression=cron_expr,
                enabled=True,
                schedule_preset=SchedulePreset.CUSTOM,
                timezone=tz,
                next_run_at=next_run,
            ))

        # Update handoff_at so the UI shows when next execution happens
        if next_run:
            workflow.handoff_at = next_run

        # Ensure workflow is active so the scheduler picks it up
        from backend.workflows.types import WorkflowStatus
        workflow.status = WorkflowStatus.ACTIVE
    elif request.timezone is not None and workflow.triggers:
        # Timezone-only update
        workflow.triggers[0].timezone = request.timezone

    if request.tasks is not None:
        from backend.workflows.types import WorkflowTask, WorkflowTaskStatus

        new_tasks = []
        for t_data in request.tasks:
            status_val = t_data.get("status", "pending")
            try:
                status = WorkflowTaskStatus(status_val)
            except ValueError:
                status = WorkflowTaskStatus.PENDING

            new_tasks.append(WorkflowTask(
                id=t_data.get("id") or gen_id("task"),
                description=t_data.get("description", ""),
                status=status,
                result=t_data.get("result", ""),
                error=t_data.get("error", "")
            ))
        workflow.tasks = new_tasks

    workflow.updated_at = datetime.now()
    store.save_workflow(workflow)
    return {"success": True}
