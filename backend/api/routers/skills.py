"""
Skills Router - Public workplace skills library.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.auth.session import get_current_user
from backend.db.stores.employee_store import EmployeeStore
from backend.services.prompt_generator import generate_public_skill
from backend.core.agents.employee.types import PublicSkill
from backend.core.workflows.utils import generate_id

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


def _parse_frontmatter(markdown: str) -> dict[str, Any]:
    if not markdown.startswith("---"):
        return {}

    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter_lines.append(line)

    data: dict[str, Any] = {}
    for raw in frontmatter_lines:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("'\"")
        if not key:
            continue
        data[key] = value
    return data


def _parse_tools(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.strip().strip("[]")
    if not cleaned:
        return []
    items = [p.strip().strip("'\"") for p in cleaned.split(",")]
    return [item for item in items if item]


def import_agency_skills_into_public_store() -> dict[str, Any]:
    """
    Import skills from frontend/public/agency-skills.json + markdown files
    into the backend public_skills table.
    """
    repo_root = Path(__file__).resolve().parents[3]
    public_root = repo_root / "frontend" / "public"
    index_path = public_root / "agency-skills.json"

    if not index_path.exists():
        raise FileNotFoundError(f"Missing skills index: {index_path}")

    raw = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("agency-skills.json must be a JSON array")

    created = 0
    updated = 0
    missing_markdown = 0

    for entry in raw:
        if not isinstance(entry, dict):
            continue

        skill_id = str(entry.get("id") or "").strip()
        category = str(entry.get("category") or "general").strip() or "general"
        name = str(entry.get("name") or "").strip()
        description = str(entry.get("description") or "").strip()
        rel_web_path = str(entry.get("path") or "").strip()

        if not skill_id:
            continue

        slug = slugify(skill_id)
        markdown = ""

        if rel_web_path:
            rel_path = rel_web_path.lstrip("/")
            markdown_path = public_root / rel_path
            if markdown_path.exists():
                markdown = markdown_path.read_text(encoding="utf-8")
            else:
                missing_markdown += 1

        frontmatter = _parse_frontmatter(markdown)
        title = str(frontmatter.get("name") or name or skill_id).strip()
        full_description = str(frontmatter.get("description") or description).strip()
        tools = _parse_tools(frontmatter.get("tools"))

        existing = store.get_public_skill(slug)
        now = datetime.now()

        skill = PublicSkill(
            id=existing.id if existing else generate_id("pskill"),
            slug=slug,
            title=title,
            description=full_description,
            category=category,
            employee_role=f"{category.replace('-', ' ').title()} Specialist",
            suggested_tools=tools,
            skill_markdown=markdown,
            notes=f"Imported from {rel_web_path}" if rel_web_path else "Imported from agency-skills index",
            source_model="agency-skills-import",
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        store.save_public_skill(skill)

        if existing:
            updated += 1
        else:
            created += 1

    return {
        "created": created,
        "updated": updated,
        "total_processed": created + updated,
        "missing_markdown": missing_markdown,
        "source_index": str(index_path),
    }


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
        owner_id=user["id"],
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
        source_model=f"user:{result.get('model', '') or ''}".rstrip(":"),
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


@router.post("/public/import-agency")
async def import_agency_skills(
    user=Depends(get_current_user),
):
    _require_user(user)
    try:
        summary = import_agency_skills_into_public_store()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc

    return {
        "success": True,
        "message": "Agency skills imported into public skill library",
        **summary,
    }
