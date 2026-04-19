from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.core.errors import AppError
from backend.db.stores.sprint_store import SprintStore
from backend.lib.auth.session import get_current_user
from backend.core.dispatch.jobs import enqueue_job, QueueFullError

router = APIRouter(prefix="/sprints")

def get_store():
    return SprintStore()

class CreateTaskRequest(BaseModel):
    title: str
    column_id: str
    requirements: str = ""
    description: str = ""
    priority: str = "medium"
    employee_id: str = ""

class UpdateTaskColumnRequest(BaseModel):
    column_id: str

class UpdateTaskDetailsRequest(BaseModel):
    title: str
    description: str
    requirements: str
    priority: Optional[str] = None

class UpdateTaskAssignmentRequest(BaseModel):
    employee_id: str

class AddMessageRequest(BaseModel):
    content: str
    sender_id: str = ""
    sender_name: str = ""
    sender_type: str = "human"
    message_type: str = "user"


@router.get("/active")
async def get_active_sprint(store: SprintStore = Depends(get_store), user=Depends(get_current_user)):
    owner_id = (user or {}).get("id", "") if isinstance(user, dict) else ""
    sprint = store.get_active_sprint(owner_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="No active sprint found")

    columns = store.get_sprint_columns(sprint["id"])
    tasks = store.get_sprint_tasks(sprint["id"])

    for task in tasks:
        task["messages"] = store.get_task_messages(task["id"])
        task["runs"] = store.list_runs_for_task(task["id"])

    return {
        "sprint": sprint,
        "columns": columns,
        "tasks": tasks
    }

@router.post("/{sprint_id}/tasks")
async def create_task(sprint_id: str, req: CreateTaskRequest, store: SprintStore = Depends(get_store), user=Depends(get_current_user)):
    owner_id = (user or {}).get("id", "") if isinstance(user, dict) else ""
    sprint = store.get_sprint(sprint_id)
    if not sprint or (owner_id and sprint.get("owner_id", "") not in (owner_id, "")):
        raise HTTPException(status_code=404, detail="Sprint not found")
    task_id = store.create_task(
        sprint_id=sprint_id,
        column_id=req.column_id,
        title=req.title,
        requirements=req.requirements,
        description=req.description,
        priority=req.priority,
        employee_id=req.employee_id
    )
    return {"task_id": task_id}

@router.patch("/tasks/{task_id}/column")
async def update_task_column(task_id: str, req: UpdateTaskColumnRequest, store: SprintStore = Depends(get_store), user=Depends(get_current_user)):
    store.update_task_column(task_id, req.column_id)
    return {"status": "success"}

@router.patch("/tasks/{task_id}/details")
async def update_task_details(task_id: str, req: UpdateTaskDetailsRequest, store: SprintStore = Depends(get_store), user=Depends(get_current_user)):
    store.update_task_details(task_id, req.title, req.description, req.requirements, req.priority)
    return {"status": "success"}

@router.patch("/tasks/{task_id}/assignment")
async def update_task_assignment(task_id: str, req: UpdateTaskAssignmentRequest, store: SprintStore = Depends(get_store), user=Depends(get_current_user)):
    store.update_task_assignment(task_id, req.employee_id)
    return {"status": "success"}

@router.post("/{sprint_id}/tasks/{task_id}/run")
async def run_task(
    sprint_id: str,
    task_id: str,
    store: SprintStore = Depends(get_store),
    user=Depends(get_current_user),
):
    sprint = store.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail=f"Sprint {sprint_id} not found")

    tasks = store.get_sprint_tasks(sprint_id)
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    employee_id = (task.get("employee_id") or "").strip()
    if not employee_id:
        raise HTTPException(status_code=400, detail="Task has no assigned employee")

    user_id = (user or {}).get("id") if isinstance(user, dict) else "anonymous"
    owner_id = user_id or ""

    try:
        job = await enqueue_job(
            kind="sprint",
            lane="sprint",
            user_id=user_id or "anonymous",
            owner_id=owner_id,
            required_employee_ids=[employee_id],
            payload={"sprint_id": sprint_id, "task_id": task_id},
        )
    except QueueFullError as e:
        raise AppError(
            code="SPRINT_TASK_RUN_QUEUE_FULL",
            message=str(e),
            status_code=429,
            retryable=True,
            details={"task_id": task_id, "sprint_id": sprint_id},
        ) from e

    return {"job_id": job.id, "status": "queued", "employee_id": employee_id}


@router.post("/tasks/{task_id}/messages")
def add_task_message(task_id: str, req: AddMessageRequest, store: SprintStore = Depends(get_store)):
    msg_id = store.add_task_message(
        task_id=task_id,
        content=req.content,
        sender_id=req.sender_id,
        sender_name=req.sender_name,
        sender_type=req.sender_type,
        message_type=req.message_type
    )
    return {"message_id": msg_id}
