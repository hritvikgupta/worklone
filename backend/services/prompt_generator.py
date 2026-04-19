"""
Prompt Generator Service — uses OpenRouter models to generate:
  1. Katy-quality system prompts for new employees
  2. Reusable workplace skills in SKILL.md format
"""

import json
import os
from typing import Any
from json import JSONDecodeError

import httpx

from backend.core.config.settings import get_settings
from backend.core.errors import (
    InvalidProviderResponseError,
    ProviderRequestError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from backend.core.logging import get_logger
from backend.core.tools.catalog import (
    list_catalog_tools,
    list_assignable_employee_tools,
    OPTIONAL_EMPLOYEE_TOOL_NAMES,
    _BUNDLE_ALIAS_TO_ROOT,
    PROVIDER_TOOL_BUNDLES,
)

logger = get_logger("services.prompt_generator")

KIMI_MODEL = "moonshotai/kimi-k2.5"
DEFAULT_SKILL_MODEL = os.getenv("OPENROUTER_SKILL_MODEL", "minimax/minimax-m2.7")

# Centralized LLM config
from backend.services.llm_config import (
    get_provider_config,
    get_user_provider_config,
    detect_provider,
    get_headers,
    get_payload_extras,
)

# Every optional tool the user can toggle in the UI
_OPTIONAL_TOOLS: list[dict] | None = None


def _get_optional_tools() -> list[dict]:
    """Return tool choices for the provision LLM.

    Integrations are exposed as bundle ROOTS only (GmailTool, SlackTool, ...),
    not their granular members. Same list the frontend Tools tab renders — so
    whatever the LLM picks will round-trip correctly and show as selected.
    """
    global _OPTIONAL_TOOLS
    if _OPTIONAL_TOOLS is None:
        _OPTIONAL_TOOLS = list_assignable_employee_tools()
    return _OPTIONAL_TOOLS


def _collapse_to_bundle_roots(tool_names: list[str]) -> list[str]:
    """Collapse any granular bundle-member name to its bundle root, dedupe, preserve order."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in tool_names or []:
        if not raw:
            continue
        name = raw.strip()
        root = _BUNDLE_ALIAS_TO_ROOT.get(name.lower())
        canonical = root if (root and root in PROVIDER_TOOL_BUNDLES) else name
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def _truncate(value: str, limit: int | None = None) -> str:
    max_length = limit or get_settings().provider_error_body_limit
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}..."


def _extract_json_payload(raw: str) -> dict[str, Any]:
    content = raw.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    try:
        return json.loads(content)
    except JSONDecodeError as exc:
        raise exc


async def _run_completion_request(
    *,
    service_name: str,
    model: str,
    system: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
    owner_id: str = "",
) -> dict[str, Any]:
    llm_config = get_user_provider_config(owner_id, model) if owner_id else get_provider_config(model)
    provider_name = llm_config.get("provider_name") or detect_provider(model)
    api_key = llm_config["api_key"]
    base_url = llm_config["base_url"]

    if not api_key:
        raise ProviderUnavailableError(service_name, provider_name, details={"model": model})

    try:
        async with httpx.AsyncClient(timeout=60.0 if max_tokens <= 2048 else 120.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    **get_headers(model),
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **get_payload_extras(model),
                },
            )
            resp.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning(
            "Provider timeout service=%s provider=%s model=%s",
            service_name,
            provider_name,
            model,
        )
        raise ProviderTimeoutError(service_name, provider_name, model) from exc
    except httpx.HTTPStatusError as exc:
        response = exc.response
        body = _truncate(response.text)
        logger.error(
            "Provider request failed service=%s provider=%s model=%s status=%s body=%s",
            service_name,
            provider_name,
            model,
            response.status_code,
            body,
        )
        raise ProviderRequestError(
            service_name,
            provider_name,
            model=model,
            upstream_status=response.status_code,
            details={"upstream_body": body},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception(
            "Provider transport error service=%s provider=%s model=%s",
            service_name,
            provider_name,
            model,
        )
        raise ProviderRequestError(
            service_name,
            provider_name,
            model=model,
            upstream_status=0,
            retryable=True,
            details={"reason": exc.__class__.__name__},
        ) from exc

    try:
        data = resp.json()
    except ValueError as exc:
        body = _truncate(resp.text)
        logger.error(
            "Provider returned non-JSON service=%s provider=%s model=%s body=%s",
            service_name,
            provider_name,
            model,
            body,
        )
        raise InvalidProviderResponseError(
            service_name,
            provider_name,
            model=model,
            details={"reason": "non_json_response", "upstream_body": body},
        ) from exc

    try:
        raw_content = data["choices"][0]["message"]["content"]
        if not isinstance(raw_content, str) or not raw_content.strip():
            raise KeyError("content")
    except (KeyError, IndexError, TypeError) as exc:
        logger.error(
            "Provider response missing content service=%s provider=%s model=%s keys=%s",
            service_name,
            provider_name,
            model,
            list(data.keys()) if isinstance(data, dict) else type(data).__name__,
        )
        raise InvalidProviderResponseError(
            service_name,
            provider_name,
            model=model,
            details={"reason": "missing_message_content"},
        ) from exc

    try:
        return _extract_json_payload(raw_content)
    except JSONDecodeError as exc:
        logger.error(
            "Provider returned invalid JSON payload service=%s provider=%s model=%s content=%s",
            service_name,
            provider_name,
            model,
            _truncate(raw_content),
        )
        raise InvalidProviderResponseError(
            service_name,
            provider_name,
            model=model,
            details={"reason": "invalid_json_payload"},
        ) from exc






SKILL_CATEGORIES = [
    "research", "coding", "devops", "analytics",
    "communication", "product", "design", "sales", "finance",
]

# ── Meta-prompt sent to Kimi K2.5 ──────────────────────────────────────────

META_PROMPT = """You are an expert AI-agent architect who designs autonomous AI employees for companies.

The user will give you an employee **name** and a **description** of what they want this employee to do. Your job is to produce a comprehensive, professional configuration for this AI employee.

Return ONLY a JSON object (no markdown fences, no explanation, no text outside the JSON):

{{
  "role": "<professional role title — e.g. Senior Data Analyst, Executive Personal Assistant, DevOps Lead>",
  "system_prompt": "<the full role-specific prompt — see structure rules below>",
  "tools": [<list of tool names from AVAILABLE_TOOLS below — use the exact "name" strings shown; for integrations always pick the provider root (e.g. "GmailTool", "SlackTool", "GoogleCalendarTool"), never individual sub-tools like "GmailSearchTool">],
  "skills": [
    {{
      "skill_name": "<skill name>",
      "category": "<one of: {categories}>",
      "proficiency_level": <0-100>,
      "description": "<one-line description>"
    }}
  ]
}}

---

## CRITICAL: How to write `system_prompt`

The system_prompt you generate is injected into a larger template that ALREADY provides these sections (so NEVER include them):
- ReAct reasoning pattern
- Workflow automation rules
- Integration protocol (credential checks)
- Memory / context management
- Response style guidelines
- Tool access listing
- Skills listing

You MUST write ONLY the **role-specific identity and responsibilities**. Follow this exact structure:

### Structure:

```
## Identity & Working Style
<3-4 sentences describing WHO this employee is — their personality, strengths, mindset, and how they approach work. Be vivid and professional. Write in second person ("You are..."). This is the employee's core identity.>

## Core Responsibilities

### 1. <Responsibility Area Name>
- <specific, actionable bullet — what they do, not how often>
- <bullet>
- <bullet>
- <bullet>

### 2. <Responsibility Area Name>
- <bullet>
- <bullet>
- <bullet>

(continue for 5-7 responsibility areas appropriate for the role)

## Domain Expertise
- <specific area of expertise>
- <specific area of expertise>
- <area of expertise>
(4-6 bullet points covering the professional knowledge this role requires)

## Operating Principles
- <principle that guides decision-making in this role>
- <principle>
- <principle>
(3-5 principles — e.g. "Always verify data from primary sources before acting on it")
```

### Prompt Quality Rules — follow ALL of these:

1. **NEVER hardcode specific times, dates, or schedules** (no "at 7:30 AM", no "every Monday"). The user configures scheduling separately via workflows. Write capabilities, not schedules.
2. **NEVER use placeholder language** like "your team" or "the company" when you can be more specific to the role.
3. **Generalize from the user's description** — if they say "manage inbox", expand that into a comprehensive set of communication management responsibilities. If they say "help with analytics", expand into the full data lifecycle. Extrapolate intelligently from what they described.
4. **Write detailed, actionable bullets** — "Triage incoming communications by urgency and required response type" is better than "Check email".
5. **Every responsibility area should have 3-5 bullets** — be thorough.
6. **Identity section must feel like a real professional** — mention specific strengths, working style, and what makes them effective. Not generic platitudes.
7. **Domain Expertise must be concrete** — name specific frameworks, methodologies, tools, or knowledge areas. Not vague categories.
8. **Operating Principles should reflect real professional judgment** — things a senior person in this role would actually live by.
9. **The total system_prompt should be 500-900 words** — dense, professional, no filler.
10. **Write everything in second person** ("You are...", "You maintain...", "You analyze...").

---

### Available tools (pick ONLY from this list — choose 2-5 that genuinely match the role)
{tools_list}

### Available public skills (already exist in the library)
{public_skills_list}

### How to handle skills
1. First, check the available public skills list above and select 3-6 that match this role.
2. If the role needs a capability NOT covered by any existing public skill, **propose it** as a new skill by giving it a title, description, and category. Mark it with `"new": true` in the JSON.
3. The backend will automatically create any proposed new skills in the public library before assigning them to the employee.

### Skill rules
- Prefer existing skills from the list above whenever possible
- For new skills: use a lowercase-hyphenated slug format (e.g. "competitive-intel-mapping")
- Set proficiency_level realistically (0-100) — not everything at 90+
- Spread across relevant categories — don't cluster all in one
- Total skills returned: 3-8

Return ONLY the JSON object. No markdown fences. No explanation before or after."""


SKILL_META_PROMPT = """You are an expert workplace capability designer creating reusable skills for AI employees.

You are generating ONE reusable workplace skill in the style of a basic SKILL.md file:
- YAML frontmatter with:
  - name
  - description
- Then markdown sections with instructions, examples, and guidelines

This skill is NOT an employee identity prompt.
It must define a reusable workplace capability, workflow, or domain procedure.
Do not write about personality, persona, biography, or role identity.

The skill must be designed for Worklone-style AI employees that:
- use a ReAct loop
- can call tools
- must create a plan first for multi-step work
- must ask for approval before executing a multi-step plan
- should think in terms of high-quality workplace execution

The skill should teach the employee:
- when to use this skill
- how to approach this class of work
- what high-quality output looks like
- what planning expectations apply
- how to use the available tools appropriately

Return ONLY a JSON object with this shape:
{{
  "skill_name": "lowercase-hyphenated-name",
  "title": "Human Readable Skill Title",
  "description": "Clear description of what this skill does and when to use it",
  "category": "workplace category",
  "suggested_tools": ["tool_name"],
  "skill_markdown": "---\\nname: ...\\ndescription: ...\\n---\\n\\n# ...",
  "notes": "short note about intended use"
}}

Rules:
- The skill must be reusable across multiple employees in a workplace, not tailored to one individual.
- The skill must focus on capability, process, decision quality, and outputs.
- Do not include any identity/persona language like "You are Alex" or "You are an assistant."
- The markdown must include:
  - a title
  - a short "When to use this skill" section
  - a clear workflow/instructions section
  - an examples section
  - a guidelines section
- The markdown should reference planning behavior when the work is multi-step:
  - create a plan first
  - get approval
  - then execute
- Keep it practical and operational, not academic.
- Make it compatible with the available tools, but do not hardcode unnecessary assumptions.
- Suggested tools must come only from the provided tool list.

Available tools:
{tools_list}

Return JSON only. No markdown fences outside the JSON."""


async def generate_employee_prompt(
    name: str,
    description: str,
    public_skills: list[dict] | None = None,
    owner_id: str = "",
) -> dict[str, Any]:
    """Call Kimi K2.5 to generate a full employee configuration.

    Returns dict with keys: role, system_prompt, tools, skills

    If public_skills is provided, the LLM will select from existing
    public skills and can propose new ones to be auto-created.
    """
    optional_tools = _get_optional_tools()
    tools_list = "\n".join(
        f"- {t['name']} ({t['category']}) — {t['description']}"
        for t in optional_tools
    )

    public_skills_list = ""
    if public_skills:
        lines = []
        for ps in public_skills:
            lines.append(
                f"- slug: {ps['slug']} | title: {ps['title']} | "
                f"description: {ps['description']} | category: {ps['category']}"
            )
        public_skills_list = "\n".join(lines)
    else:
        public_skills_list = "(No public skills available yet — propose all skills as new)"

    system = META_PROMPT.format(
        tools_list=tools_list,
        categories=", ".join(SKILL_CATEGORIES),
        public_skills_list=public_skills_list,
    )

    user_message = f"Employee name: {name}\nEmployee description: {description}"

    # Use user's configured provider if available, else fall back to KIMI_MODEL
    from backend.services.llm_config import get_user_provider_config
    user_cfg = get_user_provider_config(owner_id, "") if owner_id else None
    if user_cfg and user_cfg.get("api_key") and user_cfg.get("model"):
        use_model = user_cfg["model"]
    else:
        use_model = KIMI_MODEL
    logger.info("Generating prompt for employee '%s' via %s", name, use_model)
    result = await _run_completion_request(
        service_name="Employee prompt generation service",
        model=use_model,
        system=system,
        user_message=user_message,
        temperature=0.7,
        max_tokens=8000,
        owner_id=owner_id,
    )

    # Validate tools — collapse granular bundle members to their root, then
    # only keep names that actually exist in our assignable catalog.
    valid_tool_names = {t["name"] for t in optional_tools}
    collapsed = _collapse_to_bundle_roots(result.get("tools", []))
    result["tools"] = [t for t in collapsed if t in valid_tool_names]

    # Validate skill categories and normalize the "new" flag
    valid_cats = set(SKILL_CATEGORIES)
    for skill in result.get("skills", []):
        if skill.get("category", "") not in valid_cats:
            skill["category"] = "research"
        skill["proficiency_level"] = max(0, min(100, skill.get("proficiency_level", 50)))
        # Ensure "new" flag defaults to False
        if "new" not in skill:
            skill["new"] = False

    logger.info(
        f"Generated prompt for '{name}': role={result.get('role')}, "
        f"tools={result.get('tools')}, skills={len(result.get('skills', []))}"
    )

    return result


async def generate_public_skill(
    *,
    title: str,
    description: str,
    employee_role: str = "",
    model: str | None = None,
    owner_id: str = "",
) -> dict[str, Any]:
    """Generate a reusable workplace skill in SKILL.md format."""
    optional_tools = _get_optional_tools()
    tools_list = "\n".join(
        f"- {t['name']} ({t['category']}) — {t['description']}"
        for t in optional_tools
    )

    system = SKILL_META_PROMPT.format(tools_list=tools_list)
    user_message = (
        f"Skill title: {title.strip()}\n"
        f"Skill description: {description.strip()}\n"
        f"Reference employee role context: {employee_role.strip() or 'General workplace employee'}"
    )

    # Respect user's configured provider/model unless an explicit model was passed
    if not model and owner_id:
        from backend.services.llm_config import get_user_provider_config
        user_cfg = get_user_provider_config(owner_id, "")
        if user_cfg and user_cfg.get("api_key") and user_cfg.get("model"):
            model = user_cfg["model"]

    selected_model = model or DEFAULT_SKILL_MODEL

    logger.info("Generating public skill '%s' via %s", title, selected_model)
    result = await _run_completion_request(
        service_name="Public skill generation service",
        model=selected_model,
        system=system,
        user_message=user_message,
        temperature=0.7,
        max_tokens=4096,
        owner_id=owner_id,
    )

    valid_tool_names = {t["name"] for t in optional_tools}
    collapsed = _collapse_to_bundle_roots(result.get("suggested_tools", []))
    result["suggested_tools"] = [t for t in collapsed if t in valid_tool_names]
    result["model"] = selected_model
    # Ensure required keys exist
    result.setdefault("title", title)
    result.setdefault("description", description)
    result.setdefault("category", "general")
    result.setdefault("skill_name", title.lower().replace(" ", "-"))
    result.setdefault("skill_markdown", "")
    result.setdefault("notes", "")

    return result
