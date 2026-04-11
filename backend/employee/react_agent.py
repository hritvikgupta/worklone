"""
Generic Employee — AI Employee Agent (True ReAct)

A database-configured autonomous ReAct agent modeled directly on Katy's
architecture, with only prompt/configuration and tool loading sourced from
EmployeeStore instead of hardcoded PM defaults.
"""

import json
import os
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from backend.employee.employee_store import EmployeeStore
from backend.employee.tools.catalog import DEFAULT_EMPLOYEE_TOOL_NAMES, create_tool
from backend.employee.tools.system_tools.registry import ToolRegistry
from backend.workflows.logger import get_logger

logger = get_logger("employee_react")


GENERIC_EMPLOYEE_SYSTEM_PROMPT = """Your name is {employee_name}. You are {employee_role} — an AI employee who thinks strategically, operates autonomously, and drives high-quality outcomes.

## Who You Are
You are {employee_name}. Your role is {employee_role}. You operate with the same ReAct-style rigor, workflow clarity, and execution standards as Katy, but your identity, role, tools, and configured instructions are defined dynamically by the system.

Description:
{employee_description}

## Configured Instructions
{configured_prompt}

## Available Skills
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

## How You Work (ReAct Pattern)

You follow the ReAct pattern to solve problems autonomously:

1. **THINK** - Reason about what you know and what you need to find out
2. **ACT** - Use available tools to gather information or perform actions
3. **OBSERVE** - Process the results and update your understanding
4. **REPEAT** - Continue until you can provide a complete answer

You decide when to use tools and when to answer directly. YOU are in control.

## Important Guidelines

- Always think through problems step by step
- Use tools when you need information you don't have
- Be transparent about your reasoning process
- If a tool fails, try alternative approaches
- Provide clear, helpful final answers
- Ask clarifying questions when requirements are unclear
- Present trade-offs and options, not just one answer
- Stay aligned to your assigned role
- Use your configured instructions, skills, and assigned tools as your operating constraints

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
    ):
        self.employee_id = employee_id
        self.user_id = user_id or "anonymous"
        self.owner_id = owner_id
        self.user_context = user_context or {}
        self.store = EmployeeStore()

        full = self.store.get_employee_full(employee_id, owner_id)
        if not full:
            raise ValueError(f"Employee not found: {employee_id}")

        self.employee = full["employee"]
        self.employee_tools = full["tools"]
        self.employee_skills = full["skills"]

        self.model = model or self.employee.model or "openai/gpt-4o"
        self.tool_registry = ToolRegistry()
        self.tool_configs: Dict[str, dict] = {}
        self.missing_tools: List[str] = []

        # Session context — full conversation history
        self.messages: List[ContextMessage] = []
        self.steps: List[ReActStep] = []

        # OpenRouter config
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

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

    def _build_system_prompt(self) -> str:
        return GENERIC_EMPLOYEE_SYSTEM_PROMPT.format(
            employee_name=self.employee.name or "Employee",
            employee_role=self.employee.role or "Generalist",
            employee_description=self.employee.description or "No description provided.",
            configured_prompt=self._configured_prompt(),
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

        for employee_tool in self.employee_tools:
            if not employee_tool.is_enabled:
                continue

            tool = create_tool(employee_tool.tool_name)
            if not tool:
                self.missing_tools.append(employee_tool.tool_name)
                continue

            if tool.name in seen:
                if employee_tool.config:
                    self.tool_configs[tool.name] = employee_tool.config
                continue

            self.tool_registry.register(tool)
            self.tool_configs[tool.name] = employee_tool.config or {}
            seen.add(tool.name)

        logger.info(
            "Registered %s tools for employee=%s: %s",
            len(self.tool_registry.list_names()),
            self.employee_id,
            self.tool_registry.list_names(),
        )

    async def chat(
        self,
        message: str,
        stream: bool = True,
        emit_events: bool = False,
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

            # Single streaming LLM call with native function calling
            try:
                async for chunk in self._stream_llm(llm_messages, tools):
                    if chunk.get("type") == "content":
                        token = chunk.get("token", "")
                        if not isinstance(token, str):
                            token = str(token) if token is not None else ""
                        response_text += token
                        if stream and not emit_events:
                            yield token
                    elif chunk.get("type") == "tool_call":
                        tool_calls.append(chunk)
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

            print(f"\n{Colors.GREEN}[Employee] LLM Response ({len(response_text)} chars){Colors.ENDC}")
            print(f"{Colors.GREEN}{response_text[:500]}{'...' if len(response_text) > 500 else ''}{Colors.ENDC}")

            # Store assistant message in session context
            if response_text.strip():
                self.messages.append(ContextMessage(role="assistant", content=response_text.strip()))

            # === AGENT DECIDES: DONE OR CONTINUE? ===
            # No tool calls = agent is done thinking → final answer
            if not tool_calls:
                print(f"\n{Colors.BOLD}{Colors.GREEN}[Employee] NO TOOL CALLS — FINAL ANSWER{Colors.ENDC}")
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

                # Execute via registry
                result = await self.tool_registry.execute(
                    tool_name,
                    tool_input,
                    {
                        "user_id": self.user_id,
                        "actor_type": "employee",
                        "actor_id": self.employee_id,
                        "actor_name": self.employee.name,
                        "employee_id": self.employee_id,
                        "employee_name": self.employee.name,
                        "employee_role": self.employee.role,
                        "tool_config": self.tool_configs.get(tool_name, {}),
                        "tool_configs": self.tool_configs,
                    },
                )
                observation = result.to_observation()

                print(f"{Colors.GREEN}  Output: {observation[:300]}{'...' if len(observation) > 300 else ''}{Colors.ENDC}")

                if stream and emit_events:
                    yield {
                        "type": "tool_result",
                        "cycle": cycle_count,
                        "tool": tool_name,
                        "success": result.success,
                        "output": observation,
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

            print(f"\n{Colors.CYAN}[Employee] Continuing to next cycle...{Colors.ENDC}")
            # Loop continues — LLM will see tool results and decide next

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
            logger.error("OPENROUTER_API_KEY not set")
            yield {"type": "error", "message": "OPENROUTER_API_KEY not set"}
            return

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.employee.temperature if self.employee.temperature is not None else 0.7,
            "max_tokens": self.employee.max_tokens or 4096,
            "stream": True,
        }

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
                    "HTTP-Referer": "https://ceo-agent.local",
                    "X-Title": f"CEO Agent - {self.employee.name}",
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
