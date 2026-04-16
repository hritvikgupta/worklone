"""
Teams Router — REST API for managing teams, team members, and team runs.

Teams are groups of employees that can work together on a shared goal.
A team run is a single execution of a team — each member gets a task,
a separate agent instance is spawned for them, and all communication
is threaded through one conversation_id.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.store.team_store import TeamStore
from backend.store.employee_store import EmployeeStore
from backend.employee.types import (
    Team, TeamMember, TeamEdge,
    TeamTopology, TeamRunStatus,
)
from backend.employee.team_runner import TeamRunner
from backend.workflows.utils import generate_id
from backend.lib.auth.session import get_current_user as _resolve_user
from backend.store.auth_store import AuthDB

router = APIRouter()
team_store = TeamStore()
employee_store = EmployeeStore()
_auth_db = AuthDB()


# ─── Helpers ───

def _get_owner_id(authorization: Optional[str] = None) -> str:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        user = _auth_db.validate_session(token)
        if user and user.get("id"):
            return str(user["id"])
    return ""


# ─── Request Schemas ───

class CreateTeamRequest(BaseModel):
    name: str
    goal: str = ""
    topology: str = "graph"
    projectType: str = ""
    deadline: str = ""
    members: List[dict] = []  # [{id, name, role, task}]
    edges: List[dict] = []    # [{from, to}]
    sequenceOrder: List[str] = []
    broadcasterId: str = ""
    attachedFiles: List[str] = []

class UpdateTeamRequest(CreateTeamRequest):
    pass


class AddMemberRequest(BaseModel):
    employee_id: str
    role_in_team: str = ""


class AddEdgeRequest(BaseModel):
    from_employee_id: str
    to_employee_id: str
    trigger_condition: str = ""


class StartRunRequest(BaseModel):
    goal: str
    member_tasks: dict  # {employee_id: task_description}
    conversation_id: Optional[str] = None


# ─── Team CRUD ───

@router.post("/teams")
async def create_team(
    body: CreateTeamRequest,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    now = datetime.now()
    try:
        topology = TeamTopology(body.topology)
    except ValueError:
        topology = TeamTopology.GRAPH

    team = Team(
        id=generate_id("team"),
        name=body.name,
        goal=body.goal,
        owner_id=owner_id,
        topology=topology,
        project_type=body.projectType,
        deadline=body.deadline,
        sequence_order=body.sequenceOrder,
        broadcaster_id=body.broadcasterId,
        attached_files=body.attachedFiles,
        created_at=now,
        updated_at=now,
    )
    team_store.create_team(team)

    # Add members
    for m in body.members:
        emp_id = m.get("id", m.get("employee_id", ""))
        if not emp_id:
            continue
        emp = employee_store.get_employee(emp_id, owner_id)
        member = TeamMember(
            id=generate_id("tm"),
            team_id=team.id,
            employee_id=emp_id,
            employee_name=emp.name if emp else m.get("name", emp_id),
            role_in_team=m.get("role", m.get("role_in_team", "")),
            default_task=m.get("task", ""),
            created_at=now,
        )
        team_store.add_member(member)

    # Add edges
    for e in body.edges:
        edge = TeamEdge(
            id=generate_id("te"),
            team_id=team.id,
            from_employee_id=e.get("from", e.get("from_employee_id", "")),
            to_employee_id=e.get("to", e.get("to_employee_id", "")),
            trigger_condition=e.get("trigger_condition", ""),
            created_at=now,
        )
        team_store.add_edge(edge)

    return {
        "success": True,
        "team": _team_to_dict(team),
        "members": [_member_to_dict(m) for m in team_store.list_members(team.id)],
        "edges": [_edge_to_dict(e) for e in team_store.list_edges(team.id)],
    }


@router.get("/teams")
async def list_teams(authorization: Optional[str] = Header(None)):
    owner_id = _get_owner_id(authorization)
    teams = team_store.list_teams(owner_id)
    result = []
    for t in teams:
        members = team_store.list_members(t.id)
        edges = team_store.list_edges(t.id)
        result.append({
            **_team_to_dict(t),
            "members": [_member_to_dict(m) for m in members],
            "edges": [_edge_to_dict(e) for e in edges],
        })
    return {"success": True, "teams": result}


@router.put("/teams/{team_id}")
async def update_team(
    team_id: str,
    body: UpdateTeamRequest,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    team = team_store.get_team(team_id, owner_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        topology = TeamTopology(body.topology)
    except ValueError:
        topology = TeamTopology.GRAPH

    now = datetime.now()
    team.name = body.name
    team.goal = body.goal
    team.topology = topology
    team.project_type = body.projectType
    team.deadline = body.deadline
    team.sequence_order = body.sequenceOrder
    team.broadcaster_id = body.broadcasterId
    team.attached_files = body.attachedFiles
    team.updated_at = now

    team_store.update_team(team)

    # Completely replace members and edges
    team_store.clear_team_members(team_id)
    team_store.clear_team_edges(team_id)

    # Re-add members
    for m in body.members:
        emp_id = m.get("id", m.get("employee_id", ""))
        if not emp_id:
            continue
        emp = employee_store.get_employee(emp_id, owner_id)
        member = TeamMember(
            id=generate_id("tm"),
            team_id=team.id,
            employee_id=emp_id,
            employee_name=emp.name if emp else m.get("name", emp_id),
            role_in_team=m.get("role", m.get("role_in_team", "")),
            default_task=m.get("task", ""),
            created_at=now,
        )
        team_store.add_member(member)

    # Re-add edges
    for e in body.edges:
        edge = TeamEdge(
            id=generate_id("te"),
            team_id=team.id,
            from_employee_id=e.get("from", e.get("from_employee_id", "")),
            to_employee_id=e.get("to", e.get("to_employee_id", "")),
            trigger_condition=e.get("trigger_condition", ""),
            created_at=now,
        )
        team_store.add_edge(edge)

    return {
        "success": True,
        "team": _team_to_dict(team),
        "members": [_member_to_dict(m) for m in team_store.list_members(team.id)],
        "edges": [_edge_to_dict(e) for e in team_store.list_edges(team.id)],
    }


@router.get("/teams/{team_id}")
async def get_team(
    team_id: str,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    team = team_store.get_team(team_id, owner_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = team_store.list_members(team_id)
    edges = team_store.list_edges(team_id)
    runs = team_store.list_runs(team_id, owner_id)
    return {
        "success": True,
        "team": _team_to_dict(team),
        "members": [_member_to_dict(m) for m in members],
        "edges": [_edge_to_dict(e) for e in edges],
        "runs": [_run_to_dict(r) for r in runs],
    }


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: str,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    deleted = team_store.delete_team(team_id, owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"success": True}


# ─── Team Members ───

@router.post("/teams/{team_id}/members")
async def add_member(
    team_id: str,
    body: AddMemberRequest,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    team = team_store.get_team(team_id, owner_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    emp = employee_store.get_employee(body.employee_id, owner_id)
    member = TeamMember(
        id=generate_id("tm"),
        team_id=team_id,
        employee_id=body.employee_id,
        employee_name=emp.name if emp else body.employee_id,
        role_in_team=body.role_in_team,
        created_at=datetime.now(),
    )
    team_store.add_member(member)
    return {"success": True, "member": _member_to_dict(member)}


@router.delete("/teams/{team_id}/members/{member_id}")
async def remove_member(
    team_id: str,
    member_id: str,
    authorization: Optional[str] = Header(None),
):
    deleted = team_store.remove_member(member_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"success": True}


# ─── Team Runs ───

@router.post("/teams/{team_id}/runs")
async def start_run(
    team_id: str,
    body: StartRunRequest,
    authorization: Optional[str] = Header(None),
):
    """Start a new team run.

    member_tasks: {employee_id: task_description}
    Each employee listed must be a member of the team.
    A separate agent instance is spawned per employee.
    """
    owner_id = _get_owner_id(authorization)

    # Validate team
    team = team_store.get_team(team_id, owner_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Validate all specified employees are team members
    members = team_store.list_members(team_id)
    member_ids = {m.employee_id for m in members}
    for emp_id in body.member_tasks:
        if emp_id not in member_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Employee {emp_id} is not a member of this team",
            )

    runner = TeamRunner(team_id=team_id, owner_id=owner_id)

    try:
        run_id = await runner.start(
            goal=body.goal,
            member_tasks=body.member_tasks,
            conversation_id=body.conversation_id,
            user_id=owner_id or "anonymous",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    run = team_store.get_run(run_id)
    run_members = team_store.list_run_members(run_id)

    return {
        "success": True,
        "run_id": run_id,
        "run": _run_to_dict(run) if run else {},
        "members": [_run_member_to_dict(m) for m in run_members],
    }


@router.get("/teams/{team_id}/runs")
async def list_runs(
    team_id: str,
    authorization: Optional[str] = Header(None),
):
    owner_id = _get_owner_id(authorization)
    runs = team_store.list_runs(team_id, owner_id)
    result = []
    for r in runs:
        members = team_store.list_run_members(r.id)
        result.append({
            **_run_to_dict(r),
            "members": [_run_member_to_dict(m) for m in members],
        })
    return {"success": True, "runs": result}


@router.get("/teams/{team_id}/runs/{run_id}")
async def get_run(
    team_id: str,
    run_id: str,
    authorization: Optional[str] = Header(None),
):
    full = team_store.get_full_run(run_id)
    if not full or full["run"].team_id != team_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "success": True,
        "run": _run_to_dict(full["run"]),
        "members": [_run_member_to_dict(m) for m in full["members"]],
    }


@router.get("/teams/{team_id}/runs/{run_id}/stream")
async def stream_run(
    team_id: str,
    run_id: str,
    authorization: Optional[str] = Header(None),
):
    """SSE stream of run progress — member status changes and final results."""
    owner_id = _get_owner_id(authorization)
    team = team_store.get_team(team_id, owner_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    runner = TeamRunner(team_id=team_id, owner_id=owner_id)

    async def event_generator():
        async for event in runner.stream_run_events(run_id):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("run_complete", "error", "timeout"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/teams/{team_id}/conversation/{conversation_id}")
async def get_team_conversation(
    team_id: str,
    conversation_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get all messages in a team run conversation."""
    messages = team_store.get_conversation(conversation_id, limit=100)
    return {
        "success": True,
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": m.id,
                "sender_name": m.sender_name,
                "sender_type": m.sender_type.value,
                "recipient_name": m.recipient_name,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


# ─── Serializers ───

def _team_to_dict(t) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "goal": t.goal,
        "owner_id": t.owner_id,
        "topology": t.topology.value,
        "projectType": t.project_type,
        "deadline": t.deadline,
        "sequenceOrder": t.sequence_order,
        "broadcasterId": t.broadcaster_id,
        "attachedFiles": t.attached_files,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


def _member_to_dict(m) -> dict:
    return {
        "id": m.employee_id,  # Frontend uses employee_id as member 'id'
        "team_id": m.team_id,
        "employee_id": m.employee_id,
        "name": m.employee_name,
        "role": m.role_in_team,
        "task": m.default_task,
        "created_at": m.created_at.isoformat(),
    }


def _edge_to_dict(e) -> dict:
    return {
        "id": e.id,
        "team_id": e.team_id,
        "from": e.from_employee_id,
        "to": e.to_employee_id,
        "from_employee_id": e.from_employee_id,
        "to_employee_id": e.to_employee_id,
        "trigger_condition": e.trigger_condition,
        "created_at": e.created_at.isoformat(),
    }


def _run_to_dict(r) -> dict:
    return {
        "id": r.id,
        "team_id": r.team_id,
        "owner_id": r.owner_id,
        "conversation_id": r.conversation_id,
        "goal": r.goal,
        "status": r.status.value,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


def _run_member_to_dict(m) -> dict:
    return {
        "id": m.id,
        "run_id": m.run_id,
        "employee_id": m.employee_id,
        "employee_name": m.employee_name,
        "employee_role": m.employee_role,
        "assigned_task": m.assigned_task,
        "task_status": m.task_status.value,
        "result": m.result,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }
