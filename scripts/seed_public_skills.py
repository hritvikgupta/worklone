#!/usr/bin/env python3
"""
Generate and save a library of public workplace skills.

This script calls the internal generator service directly and saves the
resulting skills into the shared public_skills table.
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from backend.employee.types import PublicSkill
from backend.services.prompt_generator import generate_public_skill
from backend.store.employee_store import EmployeeStore
from backend.workflows.utils import generate_id


SEED_SKILLS = [
    {
        "title": "Inbox Triage and Action Routing",
        "description": "Review inbound communications, identify priority, extract action items, and structure the next steps for workplace execution.",
        "employee_role": "Executive Personal Assistant",
    },
    {
        "title": "Calendar Briefing Preparation",
        "description": "Prepare concise meeting briefs, agenda context, stakeholder notes, and action-oriented prep material before scheduled conversations.",
        "employee_role": "Executive Personal Assistant",
    },
    {
        "title": "Follow-Up Coordination",
        "description": "Track open loops, convert commitments into clear follow-ups, and keep communication sequences moving without losing context.",
        "employee_role": "Chief of Staff",
    },
    {
        "title": "Meeting Notes to Decisions",
        "description": "Turn raw meeting notes into structured decisions, owners, deadlines, and follow-up actions suitable for operational use.",
        "employee_role": "Chief of Staff",
    },
    {
        "title": "Competitive Research Synthesis",
        "description": "Research multiple competitors, compare positioning and product choices, and synthesize findings into clear workplace outputs.",
        "employee_role": "Product Manager",
    },
    {
        "title": "PRD Drafting Workflow",
        "description": "Convert a product idea or business request into a structured product requirements document with scope, assumptions, and execution clarity.",
        "employee_role": "Product Manager",
    },
    {
        "title": "Backlog Prioritization Review",
        "description": "Assess competing work items, rank them by impact and urgency, and produce a reasoned prioritization recommendation.",
        "employee_role": "Product Manager",
    },
    {
        "title": "Candidate Evaluation Pack",
        "description": "Review candidate information, synthesize strengths and risks, and produce structured evaluation artifacts for hiring workflows.",
        "employee_role": "Recruiter",
    },
    {
        "title": "Outbound Prospect Research",
        "description": "Research target accounts, extract relevant context, and prepare actionable outreach inputs for sales execution.",
        "employee_role": "Sales Development Representative",
    },
    {
        "title": "Account Plan Development",
        "description": "Build a structured account plan with goals, stakeholders, risks, next steps, and commercial opportunities.",
        "employee_role": "Account Executive",
    },
    {
        "title": "Incident Follow-Up Management",
        "description": "Transform incident details into a structured follow-up workflow with action items, ownership, communication, and documentation updates.",
        "employee_role": "Operations Manager",
    },
    {
        "title": "Dashboard Requirements Definition",
        "description": "Translate a business question into a dashboard specification with metrics, dimensions, assumptions, and stakeholder-ready framing.",
        "employee_role": "Data Analyst",
    },
]


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "skill"


async def main() -> int:
    store = EmployeeStore()
    created = 0

    for spec in SEED_SKILLS:
        print(f"Generating: {spec['title']}")
        result = await generate_public_skill(
            title=spec["title"],
            description=spec["description"],
            employee_role=spec["employee_role"],
        )
        now = datetime.now()
        skill = PublicSkill(
            id=generate_id("pskill"),
            slug=slugify(result.get("skill_name") or spec["title"]),
            title=result.get("title") or spec["title"],
            description=result.get("description") or spec["description"],
            category=result.get("category") or "general",
            employee_role=spec["employee_role"],
            suggested_tools=result.get("suggested_tools", []) or [],
            skill_markdown=result.get("skill_markdown", "") or "",
            notes=result.get("notes", "") or "",
            source_model=result.get("model", "") or "",
            created_at=now,
            updated_at=now,
        )
        store.save_public_skill(skill)
        created += 1
        print(f"Saved: {skill.slug}")

    print(f"\nSeeded {created} public skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
