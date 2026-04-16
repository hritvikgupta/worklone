"""
Skills Router - Public workplace skills library.
"""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.auth.session import get_current_user
from backend.store.employee_store import EmployeeStore
from backend.services.prompt_generator import generate_public_skill
from backend.employee.types import PublicSkill
from backend.workflows.utils import generate_id

router = APIRouter()
store = EmployeeStore()


def _require_user(user):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "skill"


@router.get("/public")
async def list_public_skills(user=Depends(get_current_user)):
    _require_user(user)
    skills = store.list_public_skills()
    return {
        "success": True,
        "skills": [
            {
                "id": skill.id,
                "slug": skill.slug,
                "title": skill.title,
                "description": skill.description,
                "category": skill.category,
                "employee_role": skill.employee_role,
                "suggested_tools": skill.suggested_tools,
                "source_model": skill.source_model,
                "created_at": skill.created_at.isoformat(),
                "updated_at": skill.updated_at.isoformat(),
            }
            for skill in skills
        ],
    }


@router.get("/public/{slug}")
async def get_public_skill_detail(slug: str, user=Depends(get_current_user)):
    _require_user(user)
    skill = store.get_public_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {
        "success": True,
        "skill": {
            "id": skill.id,
            "slug": skill.slug,
            "title": skill.title,
            "description": skill.description,
            "category": skill.category,
            "employee_role": skill.employee_role,
            "suggested_tools": skill.suggested_tools,
            "skill_markdown": skill.skill_markdown,
            "notes": skill.notes,
            "source_model": skill.source_model,
            "created_at": skill.created_at.isoformat(),
            "updated_at": skill.updated_at.isoformat(),
        },
    }


@router.post("/public")
async def create_public_skill(
    request: dict,
    user=Depends(get_current_user),
):
    _require_user(user)

    title = (request.get("title") or "").strip()
    description = (request.get("description") or "").strip()
    employee_role = (request.get("employee_role") or "General workplace").strip()

    if not title or not description:
        raise HTTPException(status_code=400, detail="title and description are required")

    result = await generate_public_skill(
        title=title,
        description=description,
        employee_role=employee_role,
    )

    now = datetime.now()
    skill = PublicSkill(
        id=generate_id("pskill"),
        slug=slugify(result.get("skill_name") or title),
        title=result.get("title") or title,
        description=result.get("description") or description,
        category=result.get("category") or "general",
        employee_role=employee_role,
        suggested_tools=result.get("suggested_tools", []) or [],
        skill_markdown=result.get("skill_markdown", "") or "",
        notes=result.get("notes", "") or "",
        source_model=result.get("model", "") or "",
        created_at=now,
        updated_at=now,
    )
    store.save_public_skill(skill)

    return {
        "success": True,
        "skill": {
            "id": skill.id,
            "slug": skill.slug,
            "title": skill.title,
            "description": skill.description,
            "category": skill.category,
            "employee_role": skill.employee_role,
            "suggested_tools": skill.suggested_tools,
            "source_model": skill.source_model,
            "created_at": skill.created_at.isoformat(),
            "updated_at": skill.updated_at.isoformat(),
        },
    }
