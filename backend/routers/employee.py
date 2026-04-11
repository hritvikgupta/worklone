"""
Employee Router — REST API for managing AI employees.

Endpoints for CRUD, tools, skills, tasks, and activity log.
This is separate from workflows (Harry) — employees are the chat-based agents (like Katy).
"""

import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from backend.employee.employee_store import EmployeeStore
from backend.employee.tools.catalog import list_catalog_tools
from backend.employee.types import (
    Employee, EmployeeTool, EmployeeSkill, EmployeeTask, EmployeeActivity,
    EmployeeStatus, TaskStatus, TaskPriority, SkillCategory, ActivityType
)
from backend.workflows.utils import generate_id
from backend.services.prompt_generator import generate_employee_prompt

router = APIRouter()
store = EmployeeStore()


# ─── Helpers ───

def _get_owner_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract owner_id from the Authorization header.
    For now, uses a default — integrate with your real auth system."""
    if authorization and authorization.startswith("Bearer "):
        # Parse token or extract user ID
        token = authorization.split(" ", 1)[1]
        # TODO: decode JWT and get user_id
        return ""
    return ""


# ─── Request/Response Schemas ───

class CreateEmployeeRequest(BaseModel):
    name: str
    role: str = ""
    avatar_url: str = ""
    description: str = ""
    system_prompt: str = ""
    model: str = "openai/gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = []  # tool names to assign
    skills: List[dict] = []  # {skill_name, category, proficiency_level, description}


class UpdateEmployeeRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    success: bool
    employee: Optional[dict] = None
    tools: Optional[List[dict]] = None
    skills: Optional[List[dict]] = None
    tasks: Optional[List[dict]] = None
    activity: Optional[List[dict]] = None
    error: Optional[str] = None


class EmployeeListResponse(BaseModel):
    success: bool
    employees: List[dict] = []
    error: Optional[str] = None


class AddToolRequest(BaseModel):
    tool_name: str
    config: dict = {}
    is_enabled: bool = True


class UpdateToolRequest(BaseModel):
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None


class AddSkillRequest(BaseModel):
    skill_name: str
    category: str = "research"
    proficiency_level: int = 50
    description: str = ""


class GeneratePromptRequest(BaseModel):
    name: str
    description: str = ""


class AddTaskRequest(BaseModel):
    task_title: str
    task_description: str = ""
    priority: str = "medium"
    tags: List[str] = []


class UpdateTaskRequest(BaseModel):
    task_title: Optional[str] = None
    task_description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None


# ─── Employee CRUD ───

@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(authorization: Optional[str] = Header(None)):
    """List all employees for the current user."""
    owner_id = _get_owner_id(authorization)
    try:
        employees = store.list_employees(owner_id)
        result = []
        for emp in employees:
            result.append({
                "id": emp.id,
                "name": emp.name,
                "role": emp.role,
                "avatar_url": emp.avatar_url,
                "status": emp.status.value,
                "description": emp.description,
                "model": emp.model,
                "is_active": emp.is_active,
                "created_at": emp.created_at.isoformat(),
                "updated_at": emp.updated_at.isoformat(),
            })
        return EmployeeListResponse(success=True, employees=result)
    except Exception as e:
        return EmployeeListResponse(success=False, error=str(e))


@router.get("/employees/tools/catalog")
async def get_tools_catalog():
    """Return only user-configurable optional tools for employee assignment."""
    catalog = [tool for tool in list_catalog_tools() if tool["is_optional"]]
    return {"success": True, "tools": catalog}


@router.post("/employees/generate-prompt")
async def generate_prompt(req: GeneratePromptRequest):
    """Use Kimi K2.5 to generate a Katy-quality system prompt for a new employee."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    try:
        result = await generate_employee_prompt(
            name=req.name.strip(),
            description=req.description.strip(),
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, authorization: Optional[str] = Header(None)):
    """Get a single employee with full details (tools, skills, tasks, activity)."""
    owner_id = _get_owner_id(authorization)
    full = store.get_employee_full(employee_id, owner_id)
    if not full:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp = full["employee"]
    return EmployeeResponse(
        success=True,
        employee={
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "avatar_url": emp.avatar_url,
            "status": emp.status.value,
            "description": emp.description,
            "system_prompt": emp.system_prompt,
            "model": emp.model,
            "is_active": emp.is_active,
            "temperature": emp.temperature,
            "max_tokens": emp.max_tokens,
            "created_at": emp.created_at.isoformat(),
            "updated_at": emp.updated_at.isoformat(),
        },
        tools=[
            {
                "id": t.id,
                "tool_name": t.tool_name,
                "is_enabled": t.is_enabled,
                "config": t.config,
                "created_at": t.created_at.isoformat(),
            }
            for t in full["tools"]
        ],
        skills=[
            {
                "id": s.id,
                "skill_name": s.skill_name,
                "category": s.category.value,
                "proficiency_level": s.proficiency_level,
                "description": s.description,
                "created_at": s.created_at.isoformat(),
            }
            for s in full["skills"]
        ],
        tasks=[
            {
                "id": t.id,
                "task_title": t.task_title,
                "task_description": t.task_description,
                "status": t.status.value,
                "priority": t.priority.value,
                "tags": t.tags,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in full["tasks"]
        ],
        activity=[
            {
                "id": a.id,
                "activity_type": a.activity_type.value,
                "message": a.message,
                "task_id": a.task_id,
                "metadata": a.metadata,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in full["activity"]
        ],
    )


@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    req: CreateEmployeeRequest,
    authorization: Optional[str] = Header(None),
):
    """Create a new employee."""
    owner_id = _get_owner_id(authorization)
    now = datetime.now()
    employee_id = generate_id()

    status = EmployeeStatus.IDLE
    employee = Employee(
        id=employee_id,
        name=req.name,
        role=req.role,
        avatar_url=req.avatar_url,
        status=status,
        description=req.description,
        system_prompt=req.system_prompt,
        model=req.model,
        owner_id=owner_id,
        is_active=True,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        created_at=now,
        updated_at=now,
    )

    try:
        store.create_employee(employee)

        # Assign tools
        for tool_name in req.tools:
            tool = EmployeeTool(
                id=generate_id(),
                employee_id=employee_id,
                tool_name=tool_name,
                is_enabled=True,
                created_at=now,
            )
            store.add_tool_to_employee(tool)

        # Assign skills
        for skill_data in req.skills:
            skill = EmployeeSkill(
                id=generate_id(),
                employee_id=employee_id,
                skill_name=skill_data.get("skill_name", ""),
                category=SkillCategory(skill_data.get("category", "research")),
                proficiency_level=skill_data.get("proficiency_level", 50),
                description=skill_data.get("description", ""),
                created_at=now,
            )
            store.add_skill_to_employee(skill)

        # Log activity
        store.log_activity(EmployeeActivity(
            id=generate_id(),
            employee_id=employee_id,
            activity_type=ActivityType.EMPLOYEE_CREATED,
            message=f"Employee '{employee.name}' was created",
            timestamp=now,
        ))

        return EmployeeResponse(success=True, employee={
            "id": employee.id,
            "name": employee.name,
            "role": employee.role,
            "avatar_url": employee.avatar_url,
            "status": employee.status.value,
            "description": employee.description,
            "model": employee.model,
            "is_active": employee.is_active,
            "created_at": employee.created_at.isoformat(),
            "updated_at": employee.updated_at.isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    req: UpdateEmployeeRequest,
    authorization: Optional[str] = Header(None),
):
    """Update an employee."""
    owner_id = _get_owner_id(authorization)
    updates = req.model_dump(exclude_unset=True)

    # Handle status conversion
    if "status" in updates and updates["status"]:
        try:
            updates["status"] = EmployeeStatus(updates["status"])
        except ValueError:
            pass

    employee = store.update_employee(employee_id, updates, owner_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Log activity
    store.log_activity(EmployeeActivity(
        id=generate_id(),
        employee_id=employee_id,
        activity_type=ActivityType.EMPLOYEE_UPDATED,
        message=f"Employee '{employee.name}' was updated",
        timestamp=datetime.now(),
    ))

    return EmployeeResponse(success=True, employee={
        "id": employee.id,
        "name": employee.name,
        "role": employee.role,
        "avatar_url": employee.avatar_url,
        "status": employee.status.value,
        "description": employee.description,
        "system_prompt": employee.system_prompt,
        "model": employee.model,
        "is_active": employee.is_active,
        "temperature": employee.temperature,
        "max_tokens": employee.max_tokens,
        "created_at": employee.created_at.isoformat(),
        "updated_at": employee.updated_at.isoformat(),
    })


@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, authorization: Optional[str] = Header(None)):
    """Delete an employee."""
    owner_id = _get_owner_id(authorization)
    deleted = store.delete_employee(employee_id, owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"success": True}


# ─── Tools ───

@router.post("/employees/{employee_id}/tools")
async def add_tool(employee_id: str, req: AddToolRequest, authorization: Optional[str] = Header(None)):
    """Add a tool to an employee."""
    owner_id = _get_owner_id(authorization)
    emp = store.get_employee(employee_id, owner_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    tool = EmployeeTool(
        id=generate_id(),
        employee_id=employee_id,
        tool_name=req.tool_name,
        is_enabled=req.is_enabled,
        config=req.config,
    )
    store.add_tool_to_employee(tool)
    return {"success": True, "tool": {"id": tool.id, "tool_name": tool.tool_name}}


@router.put("/employees/{employee_id}/tools/{tool_id}")
async def update_tool(employee_id: str, tool_id: str, req: UpdateToolRequest,
                     authorization: Optional[str] = Header(None)):
    """Update a tool configuration for an employee."""
    owner_id = _get_owner_id(authorization)
    updates = req.model_dump(exclude_unset=True)
    tool = store.update_employee_tool(employee_id, tool_id, updates, owner_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"success": True, "tool": {"id": tool.id, "is_enabled": tool.is_enabled, "config": tool.config}}


@router.delete("/employees/{employee_id}/tools/{tool_id}")
async def remove_tool(employee_id: str, tool_id: str, authorization: Optional[str] = Header(None)):
    """Remove a tool from an employee."""
    owner_id = _get_owner_id(authorization)
    removed = store.remove_tool_from_employee(employee_id, tool_id, owner_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"success": True}


# ─── Skills ───

@router.post("/employees/{employee_id}/skills")
async def add_skill(employee_id: str, req: AddSkillRequest, authorization: Optional[str] = Header(None)):
    """Add a skill to an employee."""
    owner_id = _get_owner_id(authorization)
    emp = store.get_employee(employee_id, owner_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    skill = EmployeeSkill(
        id=generate_id(),
        employee_id=employee_id,
        skill_name=req.skill_name,
        category=SkillCategory(req.category),
        proficiency_level=req.proficiency_level,
        description=req.description,
    )
    store.add_skill_to_employee(skill)
    return {"success": True, "skill": {"id": skill.id, "skill_name": skill.skill_name}}


@router.delete("/employees/{employee_id}/skills/{skill_id}")
async def remove_skill(employee_id: str, skill_id: str, authorization: Optional[str] = Header(None)):
    """Remove a skill from an employee."""
    owner_id = _get_owner_id(authorization)
    removed = store.remove_skill_from_employee(employee_id, skill_id, owner_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True}


# ─── Tasks ───

@router.post("/employees/{employee_id}/tasks")
async def create_task(employee_id: str, req: AddTaskRequest, authorization: Optional[str] = Header(None)):
    """Create a task for an employee."""
    owner_id = _get_owner_id(authorization)
    emp = store.get_employee(employee_id, owner_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    task = EmployeeTask(
        id=generate_id(),
        employee_id=employee_id,
        task_title=req.task_title,
        task_description=req.task_description,
        status=TaskStatus.TODO,
        priority=TaskPriority(req.priority),
        tags=req.tags,
    )
    store.create_task(task)
    return {"success": True, "task": {"id": task.id, "task_title": task.task_title}}


@router.put("/employees/{employee_id}/tasks/{task_id}")
async def update_task(employee_id: str, task_id: str, req: UpdateTaskRequest,
                     authorization: Optional[str] = Header(None)):
    """Update a task for an employee."""
    owner_id = _get_owner_id(authorization)
    updates = req.model_dump(exclude_unset=True)
    task = store.update_task(employee_id, task_id, updates, owner_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": {"id": task.id, "status": task.status.value}}


@router.delete("/employees/{employee_id}/tasks/{task_id}")
async def delete_task(employee_id: str, task_id: str, authorization: Optional[str] = Header(None)):
    """Delete a task for an employee."""
    owner_id = _get_owner_id(authorization)
    removed = store.delete_task(employee_id, task_id, owner_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


# ─── Activity ───

@router.get("/employees/{employee_id}/activity")
async def get_employee_activity(employee_id: str, limit: int = 50, authorization: Optional[str] = Header(None)):
    """Get activity log for an employee."""
    owner_id = _get_owner_id(authorization)
    activities = store.get_employee_activity(employee_id, owner_id, limit)
    return {
        "success": True,
        "activity": [
            {
                "id": a.id,
                "activity_type": a.activity_type.value,
                "message": a.message,
                "task_id": a.task_id,
                "metadata": a.metadata,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in activities
        ],
    }
