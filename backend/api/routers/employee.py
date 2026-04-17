"""
Employee Router — REST API for managing AI employees.

Endpoints for CRUD, tools, skills, tasks, and activity log.
This is separate from workflows (Harry) — employees are the chat-based agents (like Katy).
"""

import json
from datetime import datetime
from typing import Optional, List
import httpx

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from backend.db.stores.employee_store import EmployeeStore
from backend.core.errors import AppError
from backend.core.logging import get_logger
from backend.core.tools.catalog import list_assignable_employee_tools
from backend.services.employee_service import EmployeeService
from backend.lib.auth.session import get_current_user
from backend.core.agents.employee.types import (
    Employee, EmployeeTool, EmployeeSkill, EmployeeTask, EmployeeActivity,
    EmployeeStatus, TaskStatus, TaskPriority, SkillCategory, ActivityType
)
from backend.core.workflows.utils import generate_id
from backend.services.prompt_generator import generate_employee_prompt, generate_public_skill
from backend.db.stores.auth_store import AuthDB

router = APIRouter()
store = EmployeeStore()
employee_service = EmployeeService()
chat_db = AuthDB()
logger = get_logger("api.routers.employee")


# ─── Helpers ───

def _get_owner_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract owner_id from the Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        user = chat_db.validate_session(token)
        if user and user.get("id"):
            return str(user["id"])
    return ""


def _get_employee_with_legacy_fallback(employee_id: str, owner_id: str = ""):
    """Fetch an employee by owner, falling back to legacy unowned rows."""
    employee = store.get_employee(employee_id, owner_id)
    if employee or not owner_id:
        return employee
    return store.get_employee(employee_id, "")


def _get_employee_full_with_legacy_fallback(employee_id: str, owner_id: str = ""):
    full = store.get_employee_full(employee_id, owner_id)
    if full or not owner_id:
        return full
    return store.get_employee_full(employee_id, "")


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
    memory: List[str] = []  # file paths/names to attach


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
    tools: Optional[List[str]] = None
    skills: Optional[List[dict]] = None
    memory: Optional[List[str]] = None


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


class GenerateSkillRequest(BaseModel):
    title: str
    description: str = ""
    employee_role: str = ""
    model: Optional[str] = None


class EmployeeChatSessionCreateRequest(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = None


class EmployeeChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []
    model: Optional[str] = None
    session_id: Optional[str] = None


class EmployeeChatResumeRequest(BaseModel):
    session_id: Optional[str] = None
    approved: bool = False
    message: Optional[str] = ""
    input: Optional[dict] = None


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
        if owner_id:
            legacy_employees = store.list_employees("")
            seen_ids = {emp.id for emp in employees}
            for legacy in legacy_employees:
                if legacy.id not in seen_ids:
                    employees.append(legacy)
        result = []
        for emp in employees:
            result.append({
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
                "memory": emp.memory,
                "created_at": emp.created_at.isoformat(),
                "updated_at": emp.updated_at.isoformat(),
            })
        return EmployeeListResponse(success=True, employees=result)
    except Exception as e:
        logger.exception("Failed to list employees owner_id=%s", owner_id)
        raise AppError(
            code="EMPLOYEE_LIST_FAILED",
            message="Employees could not be loaded right now.",
            status_code=503,
            retryable=True,
        ) from e


@router.get("/employees/tools/catalog")
async def get_tools_catalog():
    """Return assignable employee tools.

    Provider integrations are exposed as provider roots (Gmail, Slack, Notion, GitHub, Jira);
    selecting one grants the employee the full provider tool bundle.
    """
    catalog = list_assignable_employee_tools()
    return {"success": True, "tools": catalog}


@router.get("/employees/models/catalog")
async def get_models_catalog(provider: str = "openrouter"):
    """Return models for employee configuration.
    
    Args:
        provider: "openrouter" or "nvidia" - defaults to "openrouter"
    """
    try:
        from backend.services.llm_provider import LLMProviderFactory
        
        llm_provider = LLMProviderFactory.get_provider(provider)
        if not llm_provider:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown provider: {provider}. Supported: openrouter, nvidia"
            )
        
        models = await llm_provider.get_models()
        
        result = []
        for model in models:
            result.append({
                "id": model.get("id", ""),
                "name": model.get("name") or model.get("id", ""),
                "description": model.get("description") or "",
                "context_length": model.get("context_length") or 0,
                "provider": model.get("provider") or provider,
            })
        
        result.sort(key=lambda item: ((item.get("name") or "").lower(), item.get("id") or ""))
        return {"success": True, "models": result, "provider": provider}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load model catalog provider=%s", provider)
        raise AppError(
            code="MODEL_CATALOG_UNAVAILABLE",
            message="The model catalog could not be loaded right now.",
            status_code=503,
            retryable=True,
            details={"provider": provider},
        ) from e


@router.get("/employees/models/providers")
async def get_available_providers():
    """Return list of available LLM providers and their status."""
    from backend.services.llm_config import get_available_providers
    return {"providers": list(get_available_providers().values())}


@router.post("/employees/generate-prompt")
async def generate_prompt(req: GeneratePromptRequest):
    """Use Kimi K2.5 to generate a Katy-quality system prompt for a new employee."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    # Fetch existing public skills to pass to the LLM
    all_skills = store.list_public_skills()
    public_skills = [
        {
            "slug": s.slug,
            "title": s.title,
            "description": s.description,
            "category": s.category,
        }
        for s in all_skills
    ]

    result = await generate_employee_prompt(
        name=req.name.strip(),
        description=req.description.strip(),
        public_skills=public_skills,
    )

    # Auto-create any proposed new skills
    from backend.core.agents.employee.types import PublicSkill
    from backend.core.workflows.utils import generate_id
    from datetime import datetime
    import re

    def slugify(value: str) -> str:
        normalized = value.strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        return normalized or "skill"

    new_skills_created = []
    for skill in result.get("skills", []):
        if skill.get("new"):
            # Generate the skill via LLM and save it
            skill_title = skill.get("skill_name", skill.get("title", "unknown"))
            skill_desc = skill.get("description", "")
            from backend.services.prompt_generator import generate_public_skill
            gen_result = await generate_public_skill(
                title=skill_title,
                description=skill_desc,
                employee_role=result.get("role", ""),
            )
            now = datetime.now()
            new_skill = PublicSkill(
                id=generate_id("pskill"),
                slug=slugify(gen_result.get("skill_name") or skill_title),
                title=gen_result.get("title") or skill_title,
                description=gen_result.get("description") or skill_desc,
                category=gen_result.get("category") or skill.get("category", "research"),
                employee_role=result.get("role", ""),
                suggested_tools=gen_result.get("suggested_tools", []) or [],
                skill_markdown=gen_result.get("skill_markdown", "") or "",
                notes=gen_result.get("notes", "") or "",
                source_model=gen_result.get("model", "") or "",
                created_at=now,
                updated_at=now,
            )
            store.save_public_skill(new_skill)
            new_skills_created.append({
                "slug": new_skill.slug,
                "title": new_skill.title,
            })
            # Update the skill in the result with the real slug
            skill["skill_name"] = new_skill.slug
            skill["title"] = new_skill.title
            skill.pop("new", None)

    return {"success": True, **result, "new_skills_created": new_skills_created}


@router.post("/employees/internal/generate-skill")
async def generate_skill(req: GenerateSkillRequest):
    """Internal-only skill generator for reviewing public workplace skill drafts."""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    result = await generate_public_skill(
        title=req.title.strip(),
        description=req.description.strip(),
        employee_role=req.employee_role.strip(),
        model=req.model.strip() if req.model else None,
    )
    return {"success": True, **result}


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, authorization: Optional[str] = Header(None)):
    """Get a single employee with full details (tools, skills, tasks, activity)."""
    owner_id = _get_owner_id(authorization)
    full = _get_employee_full_with_legacy_fallback(employee_id, owner_id)
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
            "memory": emp.memory,
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


@router.post("/employees/{employee_id}/chat")
async def chat_with_employee(
    employee_id: str,
    request: EmployeeChatRequest,
    user=Depends(get_current_user),
):
    """Send a message to a specific employee agent."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    effective_owner_id = user["id"]
    employee = store.get_employee(employee_id, effective_owner_id)
    if not employee:
        effective_owner_id = ""
        employee = store.get_employee(employee_id, effective_owner_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        response = await employee_service.chat(
            employee_id=employee_id,
            message=request.message,
            user_id=user["id"],
            owner_id=effective_owner_id,
            conversation_history=request.conversation_history or [],
            model=request.model,
            session_id=request.session_id,
        )
        return {"success": True, "response": response}
    except AppError:
        raise
    except Exception as e:
        logger.exception("Employee chat failed employee_id=%s user_id=%s", employee_id, user["id"])
        raise AppError(
            code="EMPLOYEE_CHAT_FAILED",
            message="The employee chat service could not complete the request.",
            status_code=503,
            retryable=True,
            details={"employee_id": employee_id, "session_id": request.session_id or ""},
        ) from e


@router.post("/employees/{employee_id}/chat/stream")
async def chat_with_employee_stream(
    employee_id: str,
    request: EmployeeChatRequest,
    user=Depends(get_current_user),
):
    """Stream a response from a specific employee agent."""
    from fastapi.responses import StreamingResponse

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    effective_owner_id = user["id"]
    employee = store.get_employee(employee_id, effective_owner_id)
    if not employee:
        effective_owner_id = ""
        employee = store.get_employee(employee_id, effective_owner_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    async def event_generator():
        try:
            async for event in employee_service.chat_stream(
                employee_id=employee_id,
                message=request.message,
                user_id=user["id"],
                owner_id=effective_owner_id,
                conversation_history=request.conversation_history or [],
                model=request.model,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        except AppError as e:
            yield f"data: {json.dumps({'type': 'error', 'error': e.to_payload()['error']})}\n\n"
        except Exception as e:
            logger.exception("Employee chat stream failed employee_id=%s user_id=%s", employee_id, user["id"])
            err = AppError(
                code="EMPLOYEE_CHAT_STREAM_FAILED",
                message="The employee chat stream stopped unexpectedly.",
                status_code=503,
                retryable=True,
                details={"employee_id": employee_id, "session_id": request.session_id or ""},
            )
            yield f"data: {json.dumps({'type': 'error', 'error': err.to_payload()['error']})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/employees/{employee_id}/chat/resume")
async def resume_employee_chat(
    employee_id: str,
    request: EmployeeChatResumeRequest,
    user=Depends(get_current_user),
):
    """Resume a paused employee chat with user's response (human-in-the-loop)."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    agent = employee_service.get_cached_agent(employee_id, user["id"], request.session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="No active agent session found")

    resume_message = (request.message or "").strip()
    if request.session_id and resume_message:
        employee_service.db.save_message(
            session_id=request.session_id,
            role="user",
            content=resume_message,
            model=getattr(agent, "model", None),
        )

    agent.resume_with_user_response({
        "approved": request.approved,
        "message": resume_message,
        "input": request.input or {},
    })
    return {"success": True}


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
        memory=req.memory if req.memory else [],
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
            "system_prompt": employee.system_prompt,
            "model": employee.model,
            "is_active": employee.is_active,
            "temperature": employee.temperature,
            "max_tokens": employee.max_tokens,
            "memory": employee.memory,
            "created_at": employee.created_at.isoformat(),
            "updated_at": employee.updated_at.isoformat(),
        })
    except Exception as e:
        logger.exception("Failed to create employee owner_id=%s name=%s", owner_id, req.name)
        raise AppError(
            code="EMPLOYEE_CREATE_FAILED",
            message="The employee could not be created.",
            status_code=500,
            retryable=False,
        ) from e


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    req: UpdateEmployeeRequest,
    authorization: Optional[str] = Header(None),
):
    """Update an employee."""
    owner_id = _get_owner_id(authorization)
    updates = req.model_dump(exclude_unset=True)
    tools = updates.pop("tools", None)
    skills = updates.pop("skills", None)

    # Handle status conversion
    if "status" in updates and updates["status"]:
        try:
            updates["status"] = EmployeeStatus(updates["status"])
        except ValueError:
            pass

    employee = store.update_employee(employee_id, updates, owner_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    now = datetime.now()

    if tools is not None:
        existing_tools = store.get_employee_tools(employee_id, owner_id)
        for tool in existing_tools:
            store.remove_tool_from_employee(employee_id, tool.id, owner_id)
        for tool_name in tools:
            store.add_tool_to_employee(EmployeeTool(
                id=generate_id(),
                employee_id=employee_id,
                tool_name=tool_name,
                is_enabled=True,
                created_at=now,
            ))

    if skills is not None:
        existing_skills = store.get_employee_skills(employee_id, owner_id)
        for skill in existing_skills:
            store.remove_skill_from_employee(employee_id, skill.id, owner_id)
        for skill_data in skills:
            store.add_skill_to_employee(EmployeeSkill(
                id=generate_id(),
                employee_id=employee_id,
                skill_name=skill_data.get("skill_name", ""),
                category=SkillCategory(skill_data.get("category", "research")),
                proficiency_level=skill_data.get("proficiency_level", 50),
                description=skill_data.get("description", ""),
                created_at=now,
            ))

    employee = store.get_employee(employee_id, owner_id)

    # Log activity
    store.log_activity(EmployeeActivity(
        id=generate_id(),
        employee_id=employee_id,
        activity_type=ActivityType.EMPLOYEE_UPDATED,
        message=f"Employee '{employee.name}' was updated",
        timestamp=now,
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
        "memory": employee.memory,
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


# ─── Memory ───

class UpdateMemoryRequest(BaseModel):
    memory: List[str]


@router.put("/employees/{employee_id}/memory", response_model=EmployeeResponse)
async def update_employee_memory(
    employee_id: str,
    req: UpdateMemoryRequest,
    authorization: Optional[str] = Header(None),
):
    """Update the memory (attached files) for an employee."""
    owner_id = _get_owner_id(authorization)
    employee = store.update_employee(employee_id, {"memory": req.memory}, owner_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

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
        "memory": employee.memory,
        "created_at": employee.created_at.isoformat(),
        "updated_at": employee.updated_at.isoformat(),
    })


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


# ─── Chat Sessions ───

@router.get("/employees/{employee_id}/chat/sessions")
async def list_employee_chat_sessions(employee_id: str, user=Depends(get_current_user)):
    """List chat sessions for a specific employee."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["id"]
    # Verify employee belongs to user
    employee = store.get_employee(employee_id, user_id) or store.get_employee(employee_id, "")
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    sessions = chat_db.list_chat_sessions(user_id=user_id, employee_id=employee_id)
    return {"success": True, "sessions": sessions}


@router.post("/employees/{employee_id}/chat/sessions")
async def create_employee_chat_session(
    employee_id: str,
    request: EmployeeChatSessionCreateRequest,
    user=Depends(get_current_user),
):
    """Create a new chat session for a specific employee."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["id"]
    employee = store.get_employee(employee_id, user_id) or store.get_employee(employee_id, "")
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    session_id = chat_db.create_chat_session(
        user_id=user_id,
        title=request.title or "New Chat",
        model=request.model,
        employee_id=employee_id,
    )
    session = chat_db.get_chat_session(session_id=session_id, user_id=user_id)
    return {"success": True, "session": session}


@router.get("/employees/{employee_id}/chat/sessions/{session_id}/messages")
async def get_employee_chat_messages(employee_id: str, session_id: str, user=Depends(get_current_user)):
    """Get messages for an employee chat session."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["id"]
    session = chat_db.get_chat_session(session_id=session_id, user_id=user_id)
    if not session or session.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Chat session not found for this employee")
    messages = chat_db.get_chat_history(session_id=session_id, limit=500)
    return {"success": True, "messages": messages}


@router.delete("/employees/{employee_id}/chat/sessions/{session_id}")
async def delete_employee_chat_session(employee_id: str, session_id: str, user=Depends(get_current_user)):
    """Delete a chat session for a specific employee."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["id"]
    session = chat_db.get_chat_session(session_id=session_id, user_id=user_id)
    if not session or session.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Chat session not found for this employee")
    deleted = chat_db.delete_chat_session(session_id=session_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True}
