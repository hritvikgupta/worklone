"""
Background Review — post-response self-evolution for employee agents.

After every N turns (memory) or N tool iterations (skills), this spawns a
daemon thread that silently reviews the conversation and writes improvements
to the evolution store. The main chat loop is never blocked.
"""

import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import httpx

from backend.core.agents.evolution.evolution_store import EvolutionStore
from backend.services.llm_config import get_provider_config, detect_provider, get_headers, get_payload_extras
from backend.core.logging import get_logger

logger = get_logger("background_review")

MEMORY_REVIEW_PROMPT = """You are reviewing a conversation between an AI employee and a user.
Your job: MERGE new durable facts from this conversation into the existing memory about this user.

Look for:
- Work style preferences (how they like responses structured, level of detail, tone)
- Domain expertise (what they know well vs. where they need more explanation)
- Recurring goals or projects
- Communication patterns (formal/casual, verbose/terse)
- Any explicit preferences they stated

MERGE RULES — read carefully:
1. Preserve all existing facts UNLESS this conversation explicitly contradicts or updates them.
2. Add newly learned facts on top of what's already there — do NOT rewrite from scratch.
3. If the conversation is low-signal (small talk, one-off task), return should_update=false.
4. Only drop an existing fact if the user clearly retracted or changed it.
5. Stay concise: bullet-point facts, not prose. Deduplicate.

Return a JSON object:
{{
  "should_update": true/false,
  "memory": "The full merged memory (existing facts + new ones). Bullet points. This replaces the stored memory blob."
}}

If nothing meaningful was learned, return {{"should_update": false, "memory": ""}}.

Existing memory for this user (preserve unless contradicted):
<current_memory>
{current_memory}
</current_memory>

Conversation to review:
<conversation>
{conversation}
</conversation>"""

SKILL_REVIEW_PROMPT = """You are reviewing a conversation between an AI employee and a user.
Your job: identify if the employee discovered a non-trivial, reusable procedure that should be saved as a learned skill.

A skill is worth saving if:
- The employee used trial-and-error to find the right approach
- The task required a multi-step procedure that isn't obvious
- The same situation will likely recur with this employee
- The approach revealed something non-obvious about a tool, API, or workflow

Do NOT save skills for:
- Simple one-off answers
- Basic tool usage that's already documented
- Tasks unlikely to repeat

Return a JSON object:
{{
  "should_save": true/false,
  "title": "Short skill title (5-8 words)",
  "description": "One sentence description",
  "content": "Full markdown skill document with step-by-step procedure, tips, and gotchas"
}}

If no skill is worth saving, return {{"should_save": false}}.

Employee role: {employee_role}

Conversation to review:
<conversation>
{conversation}
</conversation>"""


def _format_conversation(messages: list) -> str:
    lines = []
    for msg in messages[-40:]:  # last 40 messages to keep review focused
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
            )
        if role in ("user", "assistant") and content:
            lines.append(f"{role.upper()}: {content[:2000]}")
    return "\n\n".join(lines)


async def _call_llm_json(model: str, prompt: str) -> Optional[dict]:
    """Make a single LLM call and parse JSON from the response."""
    try:
        llm_config = get_provider_config(model)
        base_url = llm_config["base_url"]
        api_key = llm_config["api_key"]
        headers = {**get_headers(model), "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload_extras = get_payload_extras(model)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            "temperature": 0.3,
            **payload_extras,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]

        return _parse_json_loose(text)
    except Exception as e:
        logger.warning("Background review LLM call failed: %s", e)
        return None


def _parse_json_loose(text: str) -> Optional[dict]:
    """Best-effort JSON parse: try direct, then fenced block, then first {...} object."""
    if not text:
        return None
    candidates = []
    stripped = text.strip()
    candidates.append(stripped)

    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1).strip())

    # First balanced-looking {...} block
    brace = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if brace:
        candidates.append(brace.group(0))

    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            continue
    logger.warning("Background review: could not parse JSON from response (len=%d): %r", len(text), text[:300])
    return None


async def _run_memory_review(
    employee_id: str,
    user_id: str,
    model: str,
    messages: list,
    store: EvolutionStore,
) -> None:
    current_memory = store.get_user_memory(employee_id, user_id)
    conversation = _format_conversation(messages)
    prompt = MEMORY_REVIEW_PROMPT.format(
        current_memory=current_memory or "(none yet)",
        conversation=conversation,
    )
    result = await _call_llm_json(model, prompt)
    if result and result.get("should_update") and result.get("memory"):
        store.set_user_memory(employee_id, user_id, result["memory"])
        logger.info("[evolution] Memory updated for employee=%s user=%s", employee_id, user_id)


async def _run_skill_review(
    employee_id: str,
    employee_role: str,
    model: str,
    messages: list,
    store: EvolutionStore,
) -> None:
    conversation = _format_conversation(messages)
    prompt = SKILL_REVIEW_PROMPT.format(
        employee_role=employee_role,
        conversation=conversation,
    )
    result = await _call_llm_json(model, prompt)
    if result and result.get("should_save") and result.get("title") and result.get("content"):
        info = store.upsert_skill(
            employee_id=employee_id,
            title=result["title"],
            description=result.get("description", ""),
            content=result["content"],
        )
        logger.info("[evolution] Skill %s for employee=%s: %s", info["action"], employee_id, result["title"])


_REVIEW_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="evo-review")


def _thread_runner(coro_factory):
    """Run a coroutine in a new event loop. `coro_factory` is a no-arg callable that
    returns a fresh coroutine — we build it inside the worker so the coroutine is
    bound to this worker's event loop, not the submitter's."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro_factory())
    except Exception as e:
        logger.warning("Background review thread error: %s", e)
    finally:
        loop.close()


def spawn_memory_review(
    employee_id: str,
    user_id: str,
    model: str,
    messages: list,
    store: EvolutionStore,
) -> None:
    """Fire-and-forget: review conversation for user memory updates."""
    messages_snapshot = list(messages)
    _REVIEW_POOL.submit(
        _thread_runner,
        lambda: _run_memory_review(employee_id, user_id, model, messages_snapshot, store),
    )


def spawn_skill_review(
    employee_id: str,
    employee_role: str,
    model: str,
    messages: list,
    store: EvolutionStore,
) -> None:
    """Fire-and-forget: review conversation for learnable skills."""
    messages_snapshot = list(messages)
    _REVIEW_POOL.submit(
        _thread_runner,
        lambda: _run_skill_review(employee_id, employee_role, model, messages_snapshot, store),
    )
