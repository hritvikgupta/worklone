"""
Generic Employee — AI Employee Agent (True ReAct)

A database-configured autonomous ReAct agent modeled directly on Katy's
architecture, with only prompt/configuration and tool loading sourced from
EmployeeStore instead of hardcoded PM defaults.
"""

import asyncio
import json
import os
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from backend.services.llm_config import get_provider_config, detect_provider, get_headers, get_payload_extras
from backend.db.stores.employee_store import EmployeeStore
from backend.core.agents.employee.types import EmployeeActivity, ActivityType, EmployeeStatus
from backend.core.tools.catalog import DEFAULT_EMPLOYEE_TOOL_NAMES, create_tool, expand_tool_selection
from backend.core.tools.system_tools.registry import ToolRegistry
from backend.core.tools.employee_tools.ask_user_tool import ASK_USER_MARKER
from backend.core.tools.employee_tools.run_task_tool import RUN_TASK_MARKER
from backend.core.tools.employee_tools.send_message_tool import AWAIT_COWORKER_MARKER
from backend.core.logging import get_logger
from backend.core.workflows.utils import generate_id
from backend.core.agents.evolution.evolution_store import EvolutionStore
from backend.core.agents.evolution.background_review import spawn_memory_review, spawn_skill_review

logger = get_logger("employee_react")

MEMORY_NUDGE_INTERVAL = 8    # review user memory every N turns
SKILL_NUDGE_INTERVAL = 10    # review for learnable skills every N tool iterations


GENERIC_EMPLOYEE_SYSTEM_PROMPT = """Your name is {employee_name}. You are {employee_role} — an AI employee who thinks strategically, operates autonomously, and drives high-quality outcomes.

## Who You Are
You are {employee_name}, a {employee_role}. You operate autonomously using a structured reasoning loop — you think before acting, use the right tools for the job, observe results, and iterate until the task is done. You are proactive, detail-oriented, and always aligned to your assigned role.

{employee_description}

{configured_prompt}

## What You Know About This User
{user_memory_text}

## Learned Procedures (Skills You Discovered)
{learned_skills_text}

## Configured Skills
{skills_text}

## Tool Access
You only have access to the tools assigned to you in the system. Do not invent tools or claim capabilities you do not have.

Available tools:
{tools_text}

## Workflow Automation

You can create automated workflows that run on a schedule or trigger. Follow these rules STRICTLY:

### When to Create a Workflow
- **ONLY** create a workflow if the user **explicitly** asks for automation, scheduling, or recurring tasks.
- Examples that warrant a workflow: "Every morning at 9am...", "Whenever someone opens an issue...", "Automate this to run daily...", "Set up a recurring report..."
- If the user asks a **one-time** question, just answer it directly using tools. **Do NOT create a workflow.**

### Always Clarify First
- If the user describes something that COULD be automated but didn't explicitly ask, **ASK them first**:
  "Would you like me to automate this to run on a schedule? If so, how often (e.g., daily at 9am, weekly on Monday)?"
- **Do NOT assume.** Wait for their confirmation before building anything.

### Before Activating
- Show the user what the workflow will do: list the blocks, the schedule, and what each step does.
- Ask: "Shall I activate this workflow now?"
- **ONLY** call `execute_workflow` after they explicitly confirm.

### If User Wants a One-Time Action
- Just use the tools directly and give them the answer.
- **No workflow needed.** Do not schedule or save anything.

### Available Workflow Tools
- `create_workflow` — Create a new automated pipeline
- `add_block` — Add a step (trigger, tool call, LLM analysis, condition, etc.)
- `connect_blocks` — Wire steps together (A → B → C)
- `set_trigger` — Set when it runs (schedule, webhook, manual)
- `execute_workflow` — Activate it (only after user confirms)
- `list_workflows` — Show all active automations
- `monitor_workflow` — Check execution history and results

## How You Work (ReAct + Task Planning)

You follow the ReAct pattern with structured task planning. Your job is not just to act quickly. Your job is to choose the correct execution mode before acting.

### Execution Modes

You must classify every request into one of these modes before you use tools:

1. **Direct response**
   - Use this only for one bounded answer or one bounded action.
   - Examples:
     - "Explain this one issue."
     - "Draft one response."
     - "Check one record."
     - "Answer one bounded question."
   - In direct mode, you may answer directly or use tools directly.

2. **Plan-first execution**
   - Use this whenever the request involves multiple steps, multiple deliverables, multiple systems, dependencies, or processing a set/list of items.
   - This includes requests that sound simple conversationally but actually require a workflow.
   - Examples:
     - "Review a set of items, organize the findings, and produce multiple outputs."
     - "Gather information from one place, transform it, and publish it somewhere else."
     - "Analyze several inputs, make decisions, and update external systems."
     - "Carry out a workflow with ordered phases and multiple outputs."
   - In all such cases, planning is mandatory.

3. **Background execution**
   - Use this only after work has been planned and approved, when the task is long-running and should continue asynchronously.

### Non-Negotiable Planning Rule

If a request is multi-step, planning is mandatory. This is non-negotiable.

If the request includes any of the following, you MUST treat it as plan-first execution:
- More than one deliverable
- More than one destination or system
- A sequence of actions
- Processing multiple items from a list, inbox, dataset, queue, or collection
- A request containing chained actions such as "check ... summarize ... add ... send"
- Work that another professional would naturally break into phases

When that happens:
1. **PLAN** — Your FIRST action must be `manage_tasks` with `create_plan`
2. **ASK** — Your SECOND action must be `ask_user` to present the plan and wait for approval
3. **ONLY THEN EXECUTE** — After approval, execute tasks in order

For plan-first execution, you must not:
- Call any execution tool or perform any external action before creating the plan
- Skip plan approval because the request seems obvious
- Collapse a multi-step workflow into one direct execution
- Start acting just to be helpful faster

If you are deciding between direct and multi-step, bias toward planning whenever there is meaningful doubt.

### Required Task Execution Protocol

For any plan-first request, follow this exact protocol:

1. **Create the plan first**
   - Your FIRST tool call must be `manage_tasks` with `create_plan`
   - Do not call any other tool before this

2. **Show the plan and pause**
   - Call `ask_user` to present the plan and request approval
   - Wait for the user's decision before doing any execution work

3. **Execute in order after approval**
   - Use `manage_tasks` → `start_task` before beginning each task
   - Do the task using the appropriate tools
   - Use `manage_tasks` → `complete_task` when the task is done

4. **Report clearly**
   - Summarize what was completed
   - Mention any blockers, follow-ups, or outputs created

### Long-Running Work

Use `run_task_async` to execute tasks in the background while the user can continue chatting with you, but only after the work has been properly planned and approved when planning is required.

### Human-in-the-Loop

Use `ask_user` whenever you need to:
- Get approval before executing a plan
- Confirm before making irreversible changes
- Ask for clarification or missing information
- Present options and let the user choose

**NEVER proceed with destructive or irreversible actions without asking first.**

## Important Guidelines

- Always think through problems step by step
- Use tools when you need information you don't have
- Be transparent about your reasoning process
- If a tool fails, try alternative approaches
- Provide clear, helpful final answers
- Ask clarifying questions when requirements are unclear
- Present trade-offs and options, not just one answer
- Stay aligned to your assigned role
- Track your work with tasks so the user can see progress

## Integration Protocol

Before using external tools (Jira, Notion, GitHub, Slack, Gmail, analytics systems, or other integrations):
1. Check if credentials or required access are configured
2. If missing, inform the user and provide setup instructions
3. Only proceed once integrations are ready

## Memory

You maintain context across conversations and the current session:
- Previous user requests
- Previous tool results
- Prior reasoning steps
- Ongoing work, decisions, and open items relevant to your role

## Response Style

1. **Think out loud**: Share your reasoning process when it helps the user
2. **Be proactive**: Suggest next steps and considerations
3. **Ask clarifying questions**: When requirements are unclear
4. **Provide options**: Present trade-offs, not just one answer
5. **Use data**: Reference metrics, evidence, and research when available
6. **Be concise**: Busy stakeholders appreciate brevity

Current date: {current_date}
User context: {user_context}
"""


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


@dataclass
class ContextMessage:
    """A message in the conversation context."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ReActStep:
    """A single ReAct step (thought, action, observation)."""
    step_number: int
    thought: str = ""
    action: str = ""
    action_input: dict = field(default_factory=dict)
    observation: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "timestamp": self.timestamp.isoformat(),
        }


class GenericEmployeeAgent:
    """
    Generic Employee — Autonomous ReAct Agent.

    This mirrors Katy's agent flow:
    - Thinks about what to do
    - Decides which tools to call (or none) via native LLM function calling
    - Continues reasoning after tool results
    - Gives final answer when it decides it's ready

    The only differences from Katy are:
    - prompt/configuration are loaded from EmployeeStore
    - tools are loaded from assigned employee tools
    """

    def __init__(
        self,
        employee_id: str,
        user_id: Optional[str] = None,
        owner_id: str = "",
        user_context: Optional[Dict] = None,
        model: Optional[str] = None,
        team_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        self.employee_id = employee_id
        self.user_id = user_id or "anonymous"
        self.owner_id = owner_id
        self.user_context = user_context or {}
        # Team run context — present only when this agent is part of a team run
        self.team_id = team_id or ""
        self.run_id = run_id or ""
        self.store = EmployeeStore()

        full = self.store.get_employee_full(employee_id, owner_id)
        if not full and owner_id:
            # Employees created before auth was set up have owner_id=''. Try unscoped.
            full = self.store.get_employee_full(employee_id, "")
        if not full:
            raise ValueError(f"Employee not found: {employee_id}")

        self.employee = full["employee"]
        self.employee_tools = full["tools"]
        self.employee_skills = full["skills"]

        self.tool_registry = ToolRegistry()
        self.tool_configs: Dict[str, dict] = {}
        self.missing_tools: List[str] = []

        # Session context — full conversation history
        self.messages: List[ContextMessage] = []
        self.steps: List[ReActStep] = []

        # Human-in-the-loop state
        self._pending_user_response: Optional[asyncio.Future] = None
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._active_plan: Optional[Dict[str, Any]] = {}

        # Self-evolution
        self.evolution_store = EvolutionStore()
        self._turns_since_memory_review: int = 0
        self._tool_iters_since_skill_review: int = 0

        # Model priority: explicit param > employee's own config > user's LLM setting > hardcoded default
        from backend.services.llm_config import get_user_provider_config
        _employee_model = model or self.employee.model or ""
        _employee_provider = self.employee.provider or ""
        llm_config = get_user_provider_config(self.user_id, _employee_model, force_provider=_employee_provider)
        self.model = llm_config.get("model") or _employee_model or "openai/gpt-4o"
        self.provider_name = llm_config.get("provider_name") or detect_provider(self.model)
        self.api_key = llm_config["api_key"]
        self.base_url = llm_config["base_url"]

        # Register employee-assigned tools
        self._register_tools()

        logger.info(
            "Generic Employee Agent initialized for employee=%s user=%s",
            self.employee_id,
            self.user_id,
        )

    def _skills_text(self) -> str:
        if not self.employee_skills:
            return "- No explicit skills configured"

        lines = []
        for skill in self.employee_skills:
            category = skill.category.value if hasattr(skill.category, "value") else str(skill.category)
            desc = f" - {skill.description}" if skill.description else ""
            lines.append(f"- {skill.skill_name} ({category}, {skill.proficiency_level}%){desc}")
        return "\n".join(lines)

    def _configured_prompt(self) -> str:
        if self.employee.system_prompt.strip():
            return self.employee.system_prompt.strip()

        fallback = []
        if self.employee.role:
            fallback.append(f"You are responsible for operating as a {self.employee.role}.")
        if self.employee.description:
            fallback.append(self.employee.description.strip())
        fallback.append("Use the assigned tools well, reason step by step, and produce practical outputs.")
        return "\n".join(fallback)

    def _tools_text(self) -> str:
        tool_names = self.tool_registry.list_names()
        if not tool_names:
            return "- No tools assigned"
        return "\n".join(f"- {name}" for name in tool_names)

    def _user_memory_text(self) -> str:
        memory = self.evolution_store.get_user_memory(self.employee_id, self.user_id)
        if not memory:
            return "No prior context about this user yet."
        return memory

    def _learned_skills_text(self) -> str:
        skills = self.evolution_store.list_skills_full(self.employee_id, limit=10)
        if not skills:
            return "None yet — you will discover and save these over time."

        # Budget total skill content to avoid unbounded prompt growth.
        MAX_CHARS = 12000
        PER_SKILL_CAP = 3000
        blocks = []
        used = 0
        for s in skills:
            content = (s.get("content") or "").strip()
            if len(content) > PER_SKILL_CAP:
                content = content[:PER_SKILL_CAP] + "\n…(truncated)"
            header = f"### {s['title']} (v{s['version']})\n_{s.get('description', '')}_\n\n"
            block = header + content
            if used + len(block) > MAX_CHARS:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n---\n\n".join(blocks)

    def _build_system_prompt(self) -> str:
        return GENERIC_EMPLOYEE_SYSTEM_PROMPT.format(
            employee_name=self.employee.name or "Employee",
            employee_role=self.employee.role or "Generalist",
            employee_description=self.employee.description or "No description provided.",
            configured_prompt=self._configured_prompt(),
            user_memory_text=self._user_memory_text(),
            learned_skills_text=self._learned_skills_text(),
            skills_text=self._skills_text(),
            tools_text=self._tools_text(),
            current_date=datetime.now().strftime("%Y-%m-%d"),
            user_context=json.dumps(self.user_context),
        )

    def _register_tools(self):
        """Register default tools plus any employee-assigned optional tools."""
        seen = set()

        for tool_name in DEFAULT_EMPLOYEE_TOOL_NAMES:
            tool = create_tool(tool_name)
            if not tool or tool.name in seen:
                continue
            self.tool_registry.register(tool)
            self.tool_configs[tool.name] = {}
            seen.add(tool.name)

        selected_tool_names = [
            employee_tool.tool_name
            for employee_tool in self.employee_tools
            if employee_tool.is_enabled
        ]

        expanded_tool_names = expand_tool_selection(selected_tool_names)

        for tool_name in expanded_tool_names:
            source_config = next(
                (employee_tool.config for employee_tool in self.employee_tools if employee_tool.tool_name == tool_name and employee_tool.is_enabled),
                {},
            )
            if not source_config:
                source_config = next(
                    (
                        employee_tool.config
                        for employee_tool in self.employee_tools
                        if employee_tool.is_enabled
                        and tool_name in expand_tool_selection([employee_tool.tool_name])
                    ),
                    {},
                )

            tool = create_tool(tool_name)
            if not tool:
                self.missing_tools.append(tool_name)
                continue

            if tool.name in seen:
                if source_config:
                    self.tool_configs[tool.name] = source_config
                continue

            self.tool_registry.register(tool)
            self.tool_configs[tool.name] = source_config or {}
            seen.add(tool.name)

        # If this agent is part of a team run, register team-session tools:
        #   - get_my_team_context: discovery (goal, teammates, scratchpad, history)
        #   - team_memory_write:   write shared scratchpad entry
        #   - team_memory_read:    read shared scratchpad
        if self.team_id and self.run_id:
            from backend.core.tools.employee_tools.team_context_tool import GetMyTeamContextTool
            from backend.core.tools.employee_tools.team_memory_tool import (
                TeamMemoryReadTool,
                TeamMemoryWriteTool,
            )
            for team_tool in (
                GetMyTeamContextTool(),
                TeamMemoryReadTool(),
                TeamMemoryWriteTool(),
            ):
                if team_tool.name not in seen:
                    self.tool_registry.register(team_tool)
                    self.tool_configs[team_tool.name] = {}
                    seen.add(team_tool.name)
            logger.info(
                "Registered team session tools (context + memory) for employee=%s team=%s run=%s",
                self.employee_id, self.team_id, self.run_id,
            )

        logger.info(
            "Registered %s tools for employee=%s: %s",
            len(self.tool_registry.list_names()),
            self.employee_id,
            self.tool_registry.list_names(),
        )

    def _tool_context(self, tool_name: str) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "owner_id": self.owner_id,
            "actor_type": "employee",
            "actor_id": self.employee_id,
            "actor_name": self.employee.name,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name,
            "employee_role": self.employee.role,
            # Team run context — empty strings when solo, populated when in a team run
            "team_id": self.team_id,
            "run_id": self.run_id,
            "tool_config": self.tool_configs.get(tool_name, {}),
            "tool_configs": self.tool_configs,
        }

    def _format_plan_summary(self, tasks: List[Dict[str, Any]]) -> str:
        if not tasks:
            return "No tasks."
        lines = []
        for index, task in enumerate(tasks, start=1):
            status = task.get("status") or "todo"
            priority = task.get("priority") or "medium"
            task_id = task.get("task_id") or f"step_{index}"
            lines.append(f"{index}. [{task_id}] {task.get('title', 'Untitled')} ({status}, {priority})")
        return "\n".join(lines)

    def _log_activity(self, activity_type: ActivityType, message: str, task_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        try:
            self.store.log_activity(EmployeeActivity(
                id=generate_id("act"),
                employee_id=self.employee_id,
                activity_type=activity_type,
                message=message,
                task_id=task_id,
                metadata=metadata or {},
                timestamp=datetime.now(),
            ))
        except Exception as e:
            logger.warning("Failed to log employee activity: %s", e)

    def _set_employee_status(self, status: EmployeeStatus) -> None:
        try:
            self.store.update_employee(self.employee_id, {"status": status.value}, self.owner_id)
            self.employee.status = status
        except Exception as e:
            logger.warning("Failed to update employee status: %s", e)

    async def chat(
        self,
        message: str,
        stream: bool = True,
        emit_events: bool = False,
        auto_approve_human: bool = False,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Main entry point — autonomous ReAct loop.

        Flow:
        1. Send full message history + tools to LLM (one call, streaming)
        2. LLM returns content + tool_calls (or just content)
        3. If tool_calls → execute them, append results as role:"tool", go to 1
        4. If no tool_calls → that's the final answer, done

        The LLM is in full control. No keyword gates, no text parsing, no iteration caps.
        """
        logger.info("User message: %s...", message[:100])

        # Add user message to session history
        self.messages.append(ContextMessage(role="user", content=message))

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Build messages array in OpenAI format — full conversation history
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Get tools in OpenAI function-calling format
        tools = self.tool_registry.to_openai_tools()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}[Employee] NEW USER MESSAGE{Colors.ENDC}")
        print(f"{Colors.CYAN}Employee: {self.employee.name} ({self.employee.role}){Colors.ENDC}")
        print(f"{Colors.CYAN}User: {message}{Colors.ENDC}")
        print(f"{Colors.BLUE}[Employee] Tools available: {self.tool_registry.list_names()}{Colors.ENDC}")
        if self.missing_tools:
            print(f"{Colors.RED}[Employee] Missing tool mappings: {self.missing_tools}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")

        cycle_count = 0

        # === AUTONOMOUS ReAct LOOP ===
        # No iteration limit. The LLM decides when to stop.
        while True:
            cycle_count += 1
            print(f"\n{Colors.YELLOW}{'─' * 50}{Colors.ENDC}")
            print(f"{Colors.YELLOW}[Employee] CYCLE {cycle_count}{Colors.ENDC}")
            print(f"{Colors.YELLOW}{'─' * 50}{Colors.ENDC}")

            response_text = ""
            tool_calls = []
            cycle_usage = None
            cycle_start = datetime.now()

            # Single streaming LLM call with native function calling
            try:
                async for chunk in self._stream_llm(llm_messages, tools):
                    if chunk.get("type") == "content":
                        token = chunk.get("token", "")
                        if not isinstance(token, str):
                            token = str(token) if token is not None else ""
                        response_text += token
                        if stream and emit_events:
                            yield {"type": "content_token", "token": token}
                        elif stream:
                            yield token
                    elif chunk.get("type") == "tool_call":
                        tool_calls.append(chunk)
                    elif chunk.get("type") == "usage":
                        cycle_usage = chunk
                    elif chunk.get("type") == "error":
                        if stream and emit_events:
                            yield {"type": "error", "message": chunk.get("message", "Unknown error")}
                        elif stream:
                            yield f"\n[Error: {chunk.get('message', 'Unknown error')}]\n"
                        return
            except Exception as e:
                logger.exception("[Employee] LLM error: %s", e)
                if stream and emit_events:
                    yield {"type": "error", "message": str(e)}
                elif stream:
                    yield f"\n[Error: {str(e)}]\n"
                return

            # Log usage for this cycle.
            # We bill ONLY for user-visible tokens: the user's message as input
            # and the assistant's generated content as output. Tool schemas and
            # system prompt are infrastructure overhead, not metered usage.
            cycle_duration_ms = int((datetime.now() - cycle_start).total_seconds() * 1000)
            if cycle_usage:
                input_tokens = self._estimate_tokens(message) if cycle_count == 1 else 0
                output_tokens = self._estimate_tokens(response_text)
                total_tokens = input_tokens + output_tokens
                cost = self._estimate_cost(self.model, input_tokens, output_tokens)
                try:
                    self.store.log_usage(
                        employee_id=self.employee_id,
                        model=self.model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        cost=cost,
                        duration_ms=cycle_duration_ms,
                    )
                except Exception as e:
                    logger.warning("Failed to log usage: %s", e)

            print(f"\n{Colors.GREEN}[Employee] LLM Response ({len(response_text)} chars){Colors.ENDC}")
            print(f"{Colors.GREEN}{response_text[:500]}{'...' if len(response_text) > 500 else ''}{Colors.ENDC}")

            # Store assistant message in session context
            if response_text.strip():
                self.messages.append(ContextMessage(role="assistant", content=response_text.strip()))

            # === AGENT DECIDES: DONE OR CONTINUE? ===
            # No tool calls = agent is done thinking → final answer
            if not tool_calls:
                print(f"\n{Colors.BOLD}{Colors.GREEN}[Employee] NO TOOL CALLS — FINAL ANSWER{Colors.ENDC}")
                if not self._background_tasks:
                    self._set_employee_status(EmployeeStatus.IDLE)

                # Self-evolution nudges — fire-and-forget background reviews
                self._turns_since_memory_review += 1
                if self._turns_since_memory_review >= MEMORY_NUDGE_INTERVAL:
                    self._turns_since_memory_review = 0
                    spawn_memory_review(
                        employee_id=self.employee_id,
                        user_id=self.user_id,
                        model=self.model,
                        messages=[m.to_dict() for m in self.messages],
                        store=self.evolution_store,
                    )
                if self._tool_iters_since_skill_review >= SKILL_NUDGE_INTERVAL:
                    self._tool_iters_since_skill_review = 0
                    spawn_skill_review(
                        employee_id=self.employee_id,
                        employee_role=self.employee.role or "Generalist",
                        model=self.model,
                        messages=[m.to_dict() for m in self.messages],
                        store=self.evolution_store,
                    )

                # If the agent has a proposed plan but never called ask_user
                # (some LLMs just output text), auto-emit confirmation_required
                if (
                    stream and emit_events
                    and self._active_plan
                    and self._active_plan.get("status") == "proposed"
                ):
                    self._set_employee_status(EmployeeStatus.BLOCKED)
                    self._pending_user_response = asyncio.get_event_loop().create_future()
                    yield {
                        "type": "confirmation_required",
                        "cycle": cycle_count,
                        "tool": "ask_user",
                        "message": response_text.strip() or "Shall I proceed with this plan?",
                        "ask_type": "approval",
                        "options": [],
                        "plan": self._active_plan,
                    }
                    try:
                        user_response = await asyncio.wait_for(self._pending_user_response, timeout=600)
                    except asyncio.TimeoutError:
                        user_response = {"approved": False, "message": "Timed out"}
                    self._pending_user_response = None
                    approved = bool(user_response.get("approved"))
                    self._active_plan["status"] = "approved" if approved else "rejected"
                    self._set_employee_status(EmployeeStatus.WORKING if approved else EmployeeStatus.IDLE)
                    if not approved:
                        yield {"type": "final", "content": "Understood, plan rejected. Let me know if you'd like to adjust it."}
                        return
                    # Approved — inject approval into context and continue the loop
                    self.messages.append(ContextMessage(role="user", content="Approved, please proceed."))
                    llm_messages.append({"role": "user", "content": "Approved, please proceed."})
                    continue

                if stream and emit_events:
                    yield {"type": "final", "content": response_text.strip()}
                return

            # === TOOL CALLS — EXECUTE THEM ===
            print(f"\n{Colors.BOLD}{Colors.YELLOW}[Employee] TOOL CALLS DETECTED: {len(tool_calls)}{Colors.ENDC}")
            if stream and emit_events and response_text.strip():
                yield {
                    "type": "thinking",
                    "cycle": cycle_count,
                    "content": response_text.strip(),
                }

            # Build assistant message with tool_calls in OpenAI format
            assistant_tool_calls = []
            for i, tc in enumerate(tool_calls):
                assistant_tool_calls.append({
                    "id": tc.get("id", f"call_{cycle_count}_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": json.dumps(tc.get("arguments", {})),
                    },
                })

            assistant_msg = {
                "role": "assistant",
                "content": response_text if response_text.strip() else None,
                "tool_calls": assistant_tool_calls,
            }
            llm_messages.append(assistant_msg)

            # Execute each tool
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("arguments", {})
                tool_call_id = assistant_tool_calls[i]["id"]

                print(f"\n{Colors.YELLOW}[Employee] Tool #{i + 1}: {tool_name}{Colors.ENDC}")
                print(f"{Colors.YELLOW}  Input: {json.dumps(tool_input, indent=2)}{Colors.ENDC}")

                if stream and emit_events:
                    yield {
                        "type": "tool_start",
                        "cycle": cycle_count,
                        "tool": tool_name,
                        "input": tool_input,
                    }
                elif stream:
                    yield f"\nUsing {tool_name}...\n"

                result_success = False
                try:
                    # Execute via registry
                    result = await self.tool_registry.execute(
                        tool_name,
                        tool_input,
                        self._tool_context(tool_name),
                    )
                    result_success = result.success
                    observation = result.to_observation()
                    result_data = result.data if isinstance(result.data, dict) else None

                    if (
                        tool_name == "manage_tasks"
                        and result.success
                        and tool_input.get("action") == "create_plan"
                        and result_data
                        and isinstance(result_data.get("tasks"), list)
                    ):
                        plan_tasks = result_data.get("tasks", []) or []
                        self._active_plan = {
                            "mode": "multi_step",
                            "reason": "",
                            "tasks": plan_tasks,
                            "status": "approved" if auto_approve_human else "proposed",
                        }
                        print(f"{Colors.CYAN}[Employee] Proposed plan:\n{self._format_plan_summary(plan_tasks)}{Colors.ENDC}")
                        if stream and emit_events:
                            yield {
                                "type": "plan_created",
                                "mode": "multi_step",
                                "reason": "",
                                "context_summary": "",
                                "message": "",
                                "tasks": plan_tasks,
                            }

                    # --- ASK_USER: pause loop, wait for user response ---
                    if result_data and result_data.get("marker") == ASK_USER_MARKER:
                        if auto_approve_human:
                            print(f"{Colors.YELLOW}  [AUTO-APPROVE] Human interaction bypassed due to auto_approve_human=True{Colors.ENDC}")
                            user_response = {"approved": True, "message": "Auto-approved by team run policy"}
                            observation = json.dumps(user_response)
                            if self._active_plan and self._active_plan.get("status") == "proposed":
                                self._active_plan["status"] = "approved"
                            llm_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"User responded: {observation}",
                            })
                            self.steps.append(ReActStep(
                                step_number=len(self.steps) + 1,
                                thought=response_text.strip(),
                                action=tool_name,
                                action_input=tool_input,
                                observation=f"User responded: {observation}",
                            ))
                            continue
                        
                        print(f"{Colors.YELLOW}  [PAUSE] Asking user: {result_data.get('message', '')}{Colors.ENDC}")
                        plan_payload = None
                        if (
                            self._active_plan
                            and result_data.get("type", "approval") == "approval"
                            and self._active_plan.get("status") == "proposed"
                        ):
                            self._active_plan["status"] = "proposed"
                            self._set_employee_status(EmployeeStatus.BLOCKED)
                            self._log_activity(
                                ActivityType.WORKFLOW_PAUSED,
                                f"Waiting for approval on a {self._active_plan.get('mode', 'multi_step')} plan with {len(self._active_plan.get('tasks', []))} tasks",
                                metadata={"plan": self._active_plan},
                            )
                            plan_payload = self._active_plan
                        if stream and emit_events:
                            self._pending_user_response = asyncio.get_event_loop().create_future()
                            yield {
                                "type": "confirmation_required",
                                "cycle": cycle_count,
                                "tool": tool_name,
                                "message": result_data.get("message", ""),
                                "ask_type": result_data.get("type", "approval"),
                                "options": result_data.get("options", []),
                                "plan": plan_payload,
                            }
                            # Wait for user response (set by resume_with_user_response)
                            try:
                                user_response = await asyncio.wait_for(self._pending_user_response, timeout=600)
                            except asyncio.TimeoutError:
                                user_response = {"approved": False, "message": "Timed out waiting for response"}
                            self._pending_user_response = None
                            if plan_payload:
                                approved = bool(user_response.get("approved"))
                                self._active_plan["status"] = "approved" if approved else "rejected"
                                self._set_employee_status(EmployeeStatus.WORKING if approved else EmployeeStatus.BLOCKED)
                                self._log_activity(
                                    ActivityType.WORKFLOW_RESUMED if approved else ActivityType.BLOCKER_REPORTED,
                                    (
                                        f"User approved the {self._active_plan.get('mode', 'multi_step')} plan. Starting execution."
                                        if approved else
                                        "Plan was rejected by the user"
                                    ),
                                    metadata={"plan": self._active_plan},
                                )
                            observation = json.dumps(user_response)
                            # Override the tool result message for the LLM
                            llm_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"User responded: {observation}",
                            })
                            self.steps.append(ReActStep(
                                step_number=len(self.steps) + 1,
                                thought=response_text.strip(),
                                action=tool_name,
                                action_input=tool_input,
                                observation=f"User responded: {observation}",
                            ))
                            continue  # Skip normal tool result handling below
                        elif stream:
                            yield f"\n⏸ Waiting for user: {result_data.get('message', '')}\n"
                            observation = json.dumps({"approved": True, "message": "Auto-approved (non-event mode)"})

                    # --- RUN_TASK_ASYNC: spawn background task ---
                    if result_data and result_data.get("marker") == RUN_TASK_MARKER:
                        task_id = result_data.get("task_id", "")
                        instructions = result_data.get("instructions", "")
                        task_title = ""
                        if self._active_plan:
                            for plan_task in self._active_plan.get("tasks", []):
                                if plan_task.get("task_id") == task_id:
                                    task_title = str(plan_task.get("title") or "")
                                    plan_task["status"] = "in_progress"
                                    break
                        print(f"{Colors.CYAN}  [ASYNC] Spawning background task: {task_id}{Colors.ENDC}")
                        bg_task = asyncio.create_task(
                            self._run_background_task(task_id, instructions)
                        )
                        self._background_tasks[task_id] = bg_task
                        observation = f"Task {task_id} started in background. You can continue chatting."
                        if stream and emit_events:
                            yield {
                                "type": "task_started",
                                "cycle": cycle_count,
                                "task_id": task_id,
                                "task_title": task_title,
                                "instructions": instructions,
                            }

                    # --- AWAIT_COWORKER: pause loop, spawn coworker, wait for reply ---
                    if result_data and result_data.get("marker") == AWAIT_COWORKER_MARKER:
                        target_id = result_data.get("to_employee_id", "")
                        target_name = result_data.get("to_employee_name", target_id)
                        msg_id = result_data.get("message_id", "")
                        conv_id = result_data.get("conversation_id", "")
                        sent_message = result_data.get("message", "")
                        recipient_type = result_data.get("recipient_type", "employee")

                        print(f"{Colors.YELLOW}  [COWORKER] Waiting for reply from {target_name} ({target_id}){Colors.ENDC}")

                        self._set_employee_status(EmployeeStatus.BLOCKED)
                        self._log_activity(
                            ActivityType.COWORKER_MESSAGE_SENT,
                            f"Sent message to {target_name} and waiting for reply",
                            metadata={"message_id": msg_id, "to": target_id},
                        )

                        if stream and emit_events:
                            yield {
                                "type": "coworker_message_sent",
                                "cycle": cycle_count,
                                "message_id": msg_id,
                                "conversation_id": conv_id,
                                "to_employee_id": target_id,
                                "to_employee_name": target_name,
                                "recipient_type": recipient_type,
                                "message": sent_message,
                                "sender_id": self.employee_id,
                                "sender_name": self.employee.name,
                            }

                        if recipient_type == "human":
                            # Human recipient — pause like ask_user and wait
                            self._pending_user_response = asyncio.get_event_loop().create_future()
                            yield {
                                "type": "coworker_awaiting_human",
                                "cycle": cycle_count,
                                "message_id": msg_id,
                                "conversation_id": conv_id,
                                "message": sent_message,
                                "sender_name": self.employee.name,
                            }
                            try:
                                human_reply = await asyncio.wait_for(
                                    self._pending_user_response, timeout=600
                                )
                            except asyncio.TimeoutError:
                                human_reply = {"message": "Timed out waiting for human response"}
                            self._pending_user_response = None
                            self._set_employee_status(EmployeeStatus.WORKING)
                            observation = f"Human replied: {json.dumps(human_reply)}"
                        else:
                            # Employee recipient — spawn coworker agent to process the message
                            coworker_reply = await self._await_coworker_reply(
                                target_id, target_name, msg_id, conv_id, sent_message
                            )
                            self._set_employee_status(EmployeeStatus.WORKING)
                            self._log_activity(
                                ActivityType.COWORKER_MESSAGE_RECEIVED,
                                f"Received reply from {target_name}",
                                metadata={"message_id": msg_id, "from": target_id},
                            )
                            observation = f"{target_name} replied: {coworker_reply}"

                            if stream and emit_events:
                                yield {
                                    "type": "coworker_reply_received",
                                    "cycle": cycle_count,
                                    "message_id": msg_id,
                                    "conversation_id": conv_id,
                                    "from_employee_id": target_id,
                                    "from_employee_name": target_name,
                                    "reply": coworker_reply,
                                }

                        # Override the tool result for the LLM
                        llm_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": observation,
                        })
                        self.steps.append(ReActStep(
                            step_number=len(self.steps) + 1,
                            thought=response_text.strip(),
                            action=tool_name,
                            action_input=tool_input,
                            observation=observation,
                        ))
                        continue  # Skip normal tool result handling

                except Exception as e:
                    logger.exception("[Employee] Tool execution failed: %s", e)
                    observation = f"Error: Tool {tool_name} failed unexpectedly: {str(e)}"

                print(f"{Colors.GREEN}  Output: {observation[:300]}{'...' if len(observation) > 300 else ''}{Colors.ENDC}")

                if stream and emit_events:
                    yield {
                        "type": "tool_result",
                        "cycle": cycle_count,
                        "tool": tool_name,
                        "input": tool_input,
                        "success": result_success,
                        "output": observation,
                        "data": result.data if isinstance(result.data, (dict, list, str, int, float, bool)) or result.data is None else None,
                    }
                elif stream:
                    yield f"✓ {observation[:200]}{'...' if len(observation) > 200 else ''}\n\n"

                # Track the step
                self.steps.append(ReActStep(
                    step_number=len(self.steps) + 1,
                    thought=response_text.strip(),
                    action=tool_name,
                    action_input=tool_input,
                    observation=observation,
                ))

                # Append tool result in OpenAI format — LLM sees the observation next cycle
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation,
                })

            # Track tool iterations for skill nudge
            self._tool_iters_since_skill_review += len(tool_calls)

            print(f"\n{Colors.CYAN}[Employee] Continuing to next cycle...{Colors.ENDC}")
            # Loop continues — LLM will see tool results and decide next

    def resume_with_user_response(self, response: dict) -> None:
        """Resume the paused ReAct loop with user's response."""
        if self._pending_user_response and not self._pending_user_response.done():
            self._pending_user_response.set_result(response)

    async def _await_coworker_reply(
        self,
        target_employee_id: str,
        target_employee_name: str,
        message_id: str,
        conversation_id: str,
        sent_message: str,
    ) -> str:
        """Spawn a coworker agent to process our message and return their reply.

        1. Load the target employee from the store
        2. Create a GenericEmployeeAgent for them
        3. Run a single turn with our message as user input
        4. Extract the final answer as the reply
        5. Save the reply as a TeamMessage back in the conversation
        """
        from backend.db.stores.team_store import TeamStore
        from backend.core.agents.employee.types import TeamMessage, SenderType, MessageStatus
        from uuid import uuid4

        store = EmployeeStore()
        team_store = TeamStore()

        target = store.get_employee(target_employee_id, self.owner_id)
        if not target:
            return f"Error: Employee {target_employee_id} not found"

        print(f"{Colors.CYAN}  [COWORKER] Spawning {target.name} to handle message...{Colors.ENDC}")

        try:
            coworker_agent = GenericEmployeeAgent(
                employee_id=target_employee_id,
                user_id=self.user_id,
                owner_id=self.owner_id,
                user_context={
                    "from_coworker": True,
                    "sender_id": self.employee_id,
                    "sender_name": self.employee.name,
                    "sender_role": self.employee.role,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                },
            )

            # Build the prompt as if a coworker is asking
            coworker_prompt = (
                f"You received a message from your coworker {self.employee.name} "
                f"({self.employee.role}):\n\n"
                f'"{sent_message}"\n\n'
                f"Please respond to their request. Be helpful and concise. "
                f"Use your tools if needed to fulfill their request. "
                f"When you have your answer, just provide it directly."
            )

            # Run the coworker agent — collect the final answer
            reply_text = ""
            async for event in coworker_agent.chat(coworker_prompt, stream=True, emit_events=True):
                if isinstance(event, dict):
                    if event.get("type") == "final":
                        reply_text = event.get("message", "")
                    elif event.get("type") == "thinking":
                        thought = event.get("message", "")
                        if thought:
                            print(f"{Colors.BLUE}    [{target.name}] Thinking: {thought[:150]}...{Colors.ENDC}")
                elif isinstance(event, str):
                    # Streaming text — accumulate as potential reply
                    if not reply_text:
                        reply_text += event

            if not reply_text:
                reply_text = "I processed your request but have no specific response."

            # Save the reply as a TeamMessage
            reply_msg = TeamMessage(
                id=f"msg_{uuid4().hex[:12]}",
                conversation_id=conversation_id,
                sender_type=SenderType.EMPLOYEE,
                sender_id=target_employee_id,
                sender_name=target.name,
                content=reply_text,
                recipient_type=SenderType.EMPLOYEE,
                recipient_id=self.employee_id,
                recipient_name=self.employee.name,
                status=MessageStatus.PENDING,
                reply_to=message_id,
                owner_id=self.owner_id,
            )
            team_store.send_message(reply_msg)

            # Mark original message as replied
            team_store.mark_replied(message_id)

            print(f"{Colors.GREEN}  [COWORKER] {target.name} replied: {reply_text[:200]}...{Colors.ENDC}")
            return reply_text

        except Exception as e:
            logger.exception("Coworker agent %s failed: %s", target_employee_id, e)
            return f"Error: Coworker {target_employee_name} failed to respond: {str(e)}"

    async def _run_background_task(self, task_id: str, instructions: str) -> None:
        """Execute a task in the background using the employee's own tools."""
        from backend.core.agents.employee.types import TaskStatus, ActivityType, EmployeeActivity, EmployeeStatus
        from uuid import uuid4

        store = EmployeeStore()
        try:
            store.update_employee(self.employee_id, {"status": EmployeeStatus.WORKING.value}, self.owner_id)
            # Mark task as in_progress
            updated_task = store.update_task(self.employee_id, task_id, {"status": TaskStatus.IN_PROGRESS.value})
            store.log_activity(EmployeeActivity(
                id=f"act_{uuid4().hex[:12]}",
                employee_id=self.employee_id,
                activity_type=ActivityType.WORK_STARTED,
                message=f"Started background task: {updated_task.task_title if updated_task else task_id}",
                task_id=task_id,
                timestamp=datetime.now(),
            ))

            # Run a mini ReAct loop for this task
            system_prompt = self._build_system_prompt()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Execute this task:\n\n{instructions}\n\nTask ID: {task_id}. Work autonomously. When done, use manage_tasks to mark the task as complete."},
            ]
            tools = self.tool_registry.to_openai_tools()

            for cycle in range(20):  # Safety limit
                response_text = ""
                tool_calls = []

                async for chunk in self._stream_llm(messages, tools):
                    if chunk.get("type") == "content":
                        response_text += chunk.get("token", "")
                    elif chunk.get("type") == "tool_call":
                        tool_calls.append(chunk)

                if not tool_calls:
                    break

                assistant_tool_calls = []
                for i, tc in enumerate(tool_calls):
                    assistant_tool_calls.append({
                        "id": tc.get("id", f"bg_{cycle}_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", {})),
                        },
                    })
                messages.append({
                    "role": "assistant",
                    "content": response_text if response_text.strip() else None,
                    "tool_calls": assistant_tool_calls,
                })

                for i, tc in enumerate(tool_calls):
                    result = await self.tool_registry.execute(
                        tc.get("name", ""), tc.get("arguments", {}),
                        {"user_id": self.user_id, "actor_type": "employee",
                         "actor_id": self.employee_id, "employee_id": self.employee_id,
                         "employee_name": self.employee.name, "employee_role": self.employee.role,
                         "tool_config": self.tool_configs.get(tc.get("name", ""), {}),
                         "tool_configs": self.tool_configs},
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": assistant_tool_calls[i]["id"],
                        "content": result.to_observation(),
                    })

            # Mark complete if not already
            completed_task = store.update_task(self.employee_id, task_id, {"status": TaskStatus.DONE.value})
            store.log_activity(EmployeeActivity(
                id=f"act_{uuid4().hex[:12]}",
                employee_id=self.employee_id,
                activity_type=ActivityType.TASK_COMPLETED,
                message=f"Completed background task: {completed_task.task_title if completed_task else task_id}",
                task_id=task_id,
                timestamp=datetime.now(),
            ))
            store.update_employee(self.employee_id, {"status": EmployeeStatus.IDLE.value}, self.owner_id)
        except Exception as e:
            logger.exception(f"Background task {task_id} failed: {e}")
            store.update_task(self.employee_id, task_id, {"status": TaskStatus.BLOCKED.value})
            store.log_activity(EmployeeActivity(
                id=f"act_{uuid4().hex[:12]}",
                employee_id=self.employee_id,
                activity_type=ActivityType.BLOCKER_REPORTED,
                message=f"Background task {task_id} failed: {e}",
                task_id=task_id,
                timestamp=datetime.now(),
            ))
            store.update_employee(self.employee_id, {"status": EmployeeStatus.BLOCKED.value}, self.owner_id)
        finally:
            self._background_tasks.pop(task_id, None)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token count for billing — ~4 chars per token (GPT-style average).
        Excludes tool schemas and system prompt by design: we only bill for the
        user's input and the model's produced content."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD based on model pricing (per 1M tokens)."""
        # Pricing per 1M tokens: (input, output)
        pricing = {
            "openai/gpt-4o": (2.50, 10.00),
            "openai/gpt-4o-mini": (0.15, 0.60),
            "openai/gpt-4-turbo": (10.00, 30.00),
            "openai/gpt-4.1": (2.00, 8.00),
            "openai/gpt-4.1-mini": (0.40, 1.60),
            "openai/gpt-4.1-nano": (0.10, 0.40),
            "openai/o3-mini": (1.10, 4.40),
            "anthropic/claude-sonnet-4": (3.00, 15.00),
            "anthropic/claude-3.5-sonnet": (3.00, 15.00),
            "anthropic/claude-3-haiku": (0.25, 1.25),
            "google/gemini-2.0-flash-001": (0.10, 0.40),
            "google/gemini-2.5-pro-preview": (1.25, 10.00),
            "deepseek/deepseek-chat-v3-0324": (0.27, 1.10),
        }
        model_lower = model.lower()
        input_price, output_price = pricing.get(model_lower, (2.50, 10.00))
        return (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    async def _stream_llm(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream response from LLM via OpenRouter with native function calling.

        The LLM autonomously decides whether to:
        - Return content (text response / final answer)
        - Return tool_calls (actions to take)
        - Return both (thinking + actions)

        No parsing of "ACTION:" strings. No regex. Native structured output.
        """
        if not self.api_key:
            logger.error(f"{self.provider_name.upper()}_API_KEY not set")
            yield {"type": "error", "message": f"{self.provider_name.upper()}_API_KEY not set"}
            return

        logger.info(
            f"LLM CALL | Provider: {self.provider_name.upper()} | Model: {self.model} | "
            f"Messages: {len(messages)} | Tools: {len(tools) if tools else 0} | "
            f"Temperature: {self.employee.temperature if self.employee.temperature is not None else 0.7} | "
            f"Max Tokens: {self.employee.max_tokens or 4096}"
        )

        max_token_key = "max_completion_tokens" if self.provider_name == "openai" else "max_tokens"
        payload = {
            "model": self.model,
            "messages": messages,
            max_token_key: self.employee.max_tokens or 4096,
            "stream": True,
        }
        if self.provider_name != "openai":
            payload["temperature"] = self.employee.temperature if self.employee.temperature is not None else 0.7
        payload.update(get_payload_extras(self.model))

        # Request usage stats in streaming mode
        payload["stream_options"] = {"include_usage": True}

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        print(f"{Colors.CYAN}[LLM] Model: {self.model} | Messages: {len(messages)} | Tools: {len(tools) if tools else 0}{Colors.ENDC}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    **get_headers(self.model),
                },
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield {
                        "type": "error",
                        "message": f"LLM API error {response.status_code}: {error_text.decode('utf-8', errors='ignore')[:500]}",
                    }
                    return

                pending_tool_calls: Dict[int, Dict[str, Any]] = {}
                usage_data: Optional[Dict[str, Any]] = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = line[6:]
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    # Capture usage from the final chunk (OpenRouter/OpenAI stream_options)
                    if "usage" in chunk and chunk["usage"]:
                        usage_data = chunk["usage"]

                    choices = chunk.get("choices", [])
                    for choice in choices:
                        delta = choice.get("delta", {})

                        # Text content
                        if "content" in delta and delta["content"]:
                            yield {
                                "type": "content",
                                "token": delta["content"],
                            }

                        # Tool calls are streamed incrementally; accumulate them
                        for tool_call in delta.get("tool_calls", []) or []:
                            idx = tool_call.get("index", 0)
                            if idx not in pending_tool_calls:
                                pending_tool_calls[idx] = {
                                    "id": tool_call.get("id"),
                                    "name": "",
                                    "arguments_str": "",
                                }

                            function = tool_call.get("function", {})
                            if function.get("name"):
                                pending_tool_calls[idx]["name"] = function["name"]
                            if function.get("arguments"):
                                pending_tool_calls[idx]["arguments_str"] += function["arguments"]
                            if tool_call.get("id"):
                                pending_tool_calls[idx]["id"] = tool_call["id"]

                        finish_reason = choice.get("finish_reason")
                        if finish_reason == "tool_calls":
                            for pending in pending_tool_calls.values():
                                args_str = pending.get("arguments_str", "") or "{}"
                                try:
                                    arguments = json.loads(args_str)
                                except json.JSONDecodeError:
                                    arguments = {}

                                yield {
                                    "type": "tool_call",
                                    "id": pending.get("id"),
                                    "name": pending.get("name"),
                                    "arguments": arguments,
                                }
                            pending_tool_calls.clear()

                # Yield usage info if available
                if usage_data:
                    yield {
                        "type": "usage",
                        "input_tokens": usage_data.get("prompt_tokens", 0),
                        "output_tokens": usage_data.get("completion_tokens", 0),
                        "total_tokens": usage_data.get("total_tokens", 0),
                    }
