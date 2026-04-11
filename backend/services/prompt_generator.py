"""
Prompt Generator Service — uses Kimi K2.5 via OpenRouter to generate
Katy-quality system prompts for new employees.

Given a name + description from the user, this service generates:
  1. A rich system prompt matching Katy's ReAct structure
  2. Recommended role title
  3. Recommended tools from the catalog
  4. Recommended skills with categories and proficiency levels
"""

import json
import os
from typing import Any

import httpx

from backend.employee.tools.catalog import list_catalog_tools, OPTIONAL_EMPLOYEE_TOOL_NAMES
from backend.workflows.logger import get_logger

logger = get_logger("prompt_generator")

KIMI_MODEL = "moonshotai/kimi-k2"

# Every optional tool the user can toggle in the UI
_OPTIONAL_TOOLS: list[dict] | None = None


def _get_optional_tools() -> list[dict]:
    global _OPTIONAL_TOOLS
    if _OPTIONAL_TOOLS is None:
        _OPTIONAL_TOOLS = [
            t for t in list_catalog_tools() if t["is_optional"]
        ]
    return _OPTIONAL_TOOLS


SKILL_CATEGORIES = [
    "research", "coding", "devops", "analytics",
    "communication", "product", "design", "sales", "finance",
]

# ── Meta-prompt sent to Kimi K2.5 ──────────────────────────────────────────

META_PROMPT = """You are an expert AI-agent architect.  The user is creating a new AI employee for their company.  Based on the employee **name** and **description** provided, generate the following JSON object (and NOTHING else — no markdown fences, no explanation):

{{
  "role": "<short role title, e.g. Senior Data Analyst>",
  "system_prompt": "<the full configured-instructions block — see structure below>",
  "tools": [<list of tool class-names to enable from AVAILABLE_TOOLS>],
  "skills": [
    {{
      "skill_name": "<skill>",
      "category": "<one of {categories}>",
      "proficiency_level": <0-100>,
      "description": "<one-line description>"
    }}
  ]
}}

### System-prompt structure (follow EXACTLY)

The `system_prompt` value must follow this structure — it is injected into a larger template that already includes ReAct instructions, workflow rules, integration protocol, memory, and response-style sections.  So DO NOT repeat those.  Only write the **role-specific** content:

```
## Who You Are
<2-3 sentence identity paragraph — personality, strengths, working style. Make it vivid like: "You are a sharp, experienced data analyst who turns messy datasets into clear stories...">

## Core Responsibilities

### 1. <Responsibility Area>
- <bullet>
- <bullet>
- <bullet>

### 2. <Responsibility Area>
- <bullet>
- <bullet>
- <bullet>

(continue for 4-7 responsibility areas, appropriate for the role)

## Domain Expertise
- <area of expertise>
- <area of expertise>
- <area of expertise>
(3-6 bullet points)
```

### Available tools (pick ONLY from this list)
{tools_list}

### Available skill categories
{categories}

### Rules
- The system_prompt should be 400-800 words, dense and specific
- Write in second person ("You are...", "You can...")
- Be specific to the role — no generic filler
- Pick 2-5 tools that genuinely match the role
- Pick 3-7 skills with realistic proficiency levels
- Return ONLY valid JSON, no markdown code fences, no commentary"""


async def generate_employee_prompt(
    name: str,
    description: str,
) -> dict[str, Any]:
    """Call Kimi K2.5 to generate a full employee configuration.

    Returns dict with keys: role, system_prompt, tools, skills
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    optional_tools = _get_optional_tools()
    tools_list = "\n".join(
        f"- {t['name']} ({t['category']}) — {t['description']}"
        for t in optional_tools
    )

    system = META_PROMPT.format(
        tools_list=tools_list,
        categories=", ".join(SKILL_CATEGORIES),
    )

    user_message = f"Employee name: {name}\nEmployee description: {description}"

    logger.info(f"Generating prompt for employee '{name}' via {KIMI_MODEL}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": KIMI_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # remove first line
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    result = json.loads(raw)

    # Validate tools — only keep ones that actually exist in our catalog
    valid_tool_names = {t["name"] for t in optional_tools}
    result["tools"] = [t for t in result.get("tools", []) if t in valid_tool_names]

    # Validate skill categories
    valid_cats = set(SKILL_CATEGORIES)
    for skill in result.get("skills", []):
        if skill.get("category", "") not in valid_cats:
            skill["category"] = "research"
        skill["proficiency_level"] = max(0, min(100, skill.get("proficiency_level", 50)))

    logger.info(
        f"Generated prompt for '{name}': role={result.get('role')}, "
        f"tools={result.get('tools')}, skills={len(result.get('skills', []))}"
    )

    return result
