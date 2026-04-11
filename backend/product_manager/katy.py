"""
Katy — AI Product Manager Agent (True ReAct)

A TRUE autonomous ReAct agent that acts as a strategic product manager:
- Strategic Planning (vision, roadmap, competitive analysis)
- Feature Prioritization (backlog management, trade-offs)
- Cross-functional Leadership (team coordination)
- Customer Advocacy (feedback gathering, user research)
- Data-Driven Decisions (metrics, A/B tests)
- Go-to-Market (launches, positioning)
- Requirements Definition (PRDs, user stories)

Uses native LLM function calling — NO hardcoding, NO iteration limits,
NO keyword matching, NO regex parsing. The LLM decides everything.

Reference: https://www.ibm.com/think/topics/react-agent
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from backend.workflows.tools.registry import ToolRegistry
from backend.workflows.tools.base import ToolResult
from backend.workflows.tools.llm_tool import LLMTool
from backend.workflows.tools.http_tool import HTTPTool
from backend.workflows.tools.function_tool import FunctionTool
from backend.workflows.tools.slack_tool import SlackTool
from backend.workflows.tools.gmail_tool import GmailTool
from backend.workflows.store import WorkflowStore
from backend.workflows.logger import get_logger

# Import PM-specific tools
from backend.product_manager.tools.jira_tool import JiraTool
from backend.product_manager.tools.notion_tool import NotionTool
from backend.product_manager.tools.analytics_tool import AnalyticsTool
from backend.product_manager.tools.research_tool import ResearchTool
from backend.product_manager.tools.github_tool import GitHubTool
from backend.product_manager.types import PMContext, UserInsight, ProductDecision
from backend.product_manager.pm_tools import create_pm_tools

logger = get_logger("katy")


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


KATY_SYSTEM_PROMPT = """Your name is Katy. You are a Senior Product Manager — an AI product manager who thinks strategically, advocates for users, and drives product success.

## Who You Are
You are Katy — a sharp, experienced PM who can handle anything from vision setting to sprint planning. You think in systems, prioritize ruthlessly, and always put the customer first. You work with CEOs, engineers, designers, and marketers to build products that matter.

## Core Responsibilities

### 1. Strategic Planning
- Define and refine product vision and roadmap
- Conduct market research and competitive analysis
- Identify customer needs and pain points
- Set product strategy aligned with business goals

### 2. Feature Prioritization
- Manage and prioritize the product backlog
- Make trade-off decisions between features
- Balance customer needs, technical constraints, and business value
- Define MVP scope and iterative releases

### 3. Cross-functional Leadership
- Coordinate between engineering, design, marketing, and sales
- Facilitate communication across departments
- Remove blockers and enable team productivity
- Align stakeholders on product direction

### 4. Customer Advocacy
- Gather and analyze user feedback
- Conduct user interviews and usability testing
- Translate customer insights into product requirements
- Ensure the product solves real user problems

### 5. Data-Driven Decision Making
- Define and track key product metrics
- Analyze usage data and A/B test results
- Make informed decisions based on data
- Measure product success and ROI

### 6. Go-to-Market
- Work with marketing on launch plans
- Create product positioning and messaging
- Train sales and support teams
- Define pricing and packaging strategies

### 7. Requirements Definition
- Write user stories and product specifications
- Create wireframes and user flows (with designers)
- Define acceptance criteria
- Document functional and non-functional requirements

## Workflow Automation

You can create automated workflows that run on a schedule or trigger. Follow these rules STRICTLY:

### When to Create a Workflow
- **ONLY** create a workflow if the user **explicitly** asks for automation, scheduling, or recurring tasks.
- Examples that warrant a workflow: "Every morning at 9am...", "Whenever someone opens an issue...", "Automate this to run daily...", "Set up a recurring report..."
- If the user asks a **one-time** question (e.g., "What are my open issues?"), just answer it directly using tools. **Do NOT create a workflow.**

### Always Clarify First
- If the user describes something that COULD be automated but didn't explicitly ask, **ASK them first**:
  "Would you like me to automate this to run on a schedule? If so, how often (e.g., daily at 9am, weekly on Monday)?"
- **Do NOT assume.** Wait for their confirmation before building anything.

### Before Activating
- Show the user what the workflow will do: list the blocks, the schedule, and what each step does.
- Ask: "Shall I activate this workflow now?"
- **ONLY** call `execute_workflow` after they explicitly confirm.

### If User Wants a One-Time Action
- Just use the tools directly (GitHub, Slack, LLM, etc.) and give them the answer.
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
- Reference metrics and research when available

## Integration Protocol

Before using external tools (Jira, Notion, etc.):
1. Check if credentials are configured
2. If missing, inform the user and provide setup instructions
3. Only proceed once integrations are ready

## Memory

You maintain context across conversations:
- Product roadmap and vision
- Customer insights and feedback
- Previous decisions and their outcomes
- Key metrics and goals

## Response Style

1. **Think out loud**: Share your reasoning process
2. **Be proactive**: Suggest next steps and considerations
3. **Ask clarifying questions**: When requirements are unclear
4. **Provide options**: Present trade-offs, not just one answer
5. **Use data**: Reference metrics and research when available
6. **Be concise**: Busy stakeholders appreciate brevity

Current date: {current_date}
User context: {user_context}
"""


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


class KatyPMAgent:
    """
    Katy — Autonomous ReAct Product Manager Agent.

    The agent is in FULL control:
    - Thinks about what to do
    - Decides which tools to call (or none) via native LLM function calling
    - Continues reasoning after tool results
    - Gives final answer when IT decides it's ready

    NO LOOPS WITH LIMITS. NO KEYWORD MATCHING. NO REGEX PARSING.
    The agent runs until it responds to the user.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        user_context: Optional[Dict] = None,
        model: Optional[str] = None,
    ):
        self.user_id = user_id or "anonymous"
        self.user_context = user_context or {}
        self.model = model or "openai/gpt-4o"
        self.tool_registry = ToolRegistry()
        self.store = WorkflowStore()
        self.pm_context = PMContext(user_id=self.user_id)

        # Session context — full conversation history
        self.messages: List[ContextMessage] = []
        self.steps: List[ReActStep] = []

        # OpenRouter config
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

        # Register all tools
        self._register_tools()

        logger.info(f"Katy PM Agent initialized for user: {self.user_id}")

    def _register_tools(self):
        """Register all available tools."""
        # Communication tools
        self.tool_registry.register(SlackTool())
        self.tool_registry.register(GmailTool())
        self.tool_registry.register(HTTPTool())
        self.tool_registry.register(FunctionTool())

        # PM-specific tools
        self.tool_registry.register(JiraTool())
        self.tool_registry.register(NotionTool())
        self.tool_registry.register(AnalyticsTool())
        self.tool_registry.register(ResearchTool())
        self.tool_registry.register(GitHubTool())

        # Workflow creation tools (so Katy can build automations)
        from backend.workflows.coworker_tools import create_workflow_tools
        for tool in create_workflow_tools():
            self.tool_registry.register(tool)

        # High-level PM tools
        pm_tools = create_pm_tools()
        for tool in pm_tools:
            self.tool_registry.register(tool)

        logger.info(f"Registered {len(self.tool_registry.list_names())} tools")

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
        logger.info(f"User message: {message[:100]}...")

        # Add user message to session history
        self.messages.append(ContextMessage(role="user", content=message))

        # Build system prompt
        system_prompt = KATY_SYSTEM_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            user_context=json.dumps(self.user_context),
        )

        # Build messages array in OpenAI format — full conversation history
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Get tools in OpenAI function-calling format
        tools = self.tool_registry.to_openai_tools()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}[Katy] NEW USER MESSAGE{Colors.ENDC}")
        print(f"{Colors.CYAN}User: {message}{Colors.ENDC}")
        print(f"{Colors.BLUE}[Katy] Tools available: {self.tool_registry.list_names()}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")

        cycle_count = 0

        # === AUTONOMOUS ReAct LOOP ===
        # No iteration limit. The LLM decides when to stop.
        while True:
            cycle_count += 1
            print(f"\n{Colors.YELLOW}{'─' * 50}{Colors.ENDC}")
            print(f"{Colors.YELLOW}[Katy] CYCLE {cycle_count}{Colors.ENDC}")
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
                logger.exception(f"[Katy] LLM error: {e}")
                if stream and emit_events:
                    yield {"type": "error", "message": str(e)}
                elif stream:
                    yield f"\n[Error: {str(e)}]\n"
                return

            print(f"\n{Colors.GREEN}[Katy] LLM Response ({len(response_text)} chars){Colors.ENDC}")
            print(f"{Colors.GREEN}{response_text[:500]}{'...' if len(response_text) > 500 else ''}{Colors.ENDC}")

            # Store assistant message in session context
            if response_text.strip():
                self.messages.append(ContextMessage(role="assistant", content=response_text.strip()))

            # === AGENT DECIDES: DONE OR CONTINUE? ===
            # No tool calls = agent is done thinking → final answer
            if not tool_calls:
                print(f"\n{Colors.BOLD}{Colors.GREEN}[Katy] NO TOOL CALLS — FINAL ANSWER{Colors.ENDC}")
                if stream and emit_events:
                    yield {"type": "final", "content": response_text.strip()}
                return

            # === TOOL CALLS — EXECUTE THEM ===
            print(f"\n{Colors.BOLD}{Colors.YELLOW}[Katy] TOOL CALLS DETECTED: {len(tool_calls)}{Colors.ENDC}")
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

                print(f"\n{Colors.YELLOW}[Katy] Tool #{i + 1}: {tool_name}{Colors.ENDC}")
                print(f"{Colors.YELLOW}  Input: {json.dumps(tool_input, indent=2)}{Colors.ENDC}")

                if stream and emit_events:
                    yield {
                        "type": "tool_start",
                        "cycle": cycle_count,
                        "tool": tool_name,
                        "input": tool_input,
                    }
                elif stream:
                    yield f"\n🔧 Using {tool_name}...\n"

                # Execute via registry
                result = await self.tool_registry.execute(
                    tool_name, tool_input, {"user_id": self.user_id}
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

            print(f"\n{Colors.CYAN}[Katy] Continuing to next cycle...{Colors.ENDC}")
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
            "temperature": 0.7,
            "max_tokens": 4096,
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
                    "X-Title": "CEO Agent - Katy PM",
                },
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"LLM API error {response.status_code}: {error_text.decode()}")
                    yield {"type": "error", "message": f"API error {response.status_code}: {error_text.decode()[:300]}"}
                    return

                current_tool_calls = {}

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data = line[6:]
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})

                        # Content tokens — stream them to user
                        if "content" in delta and delta["content"]:
                            yield {"type": "content", "token": delta["content"]}

                        # Tool calls — accumulate (streamed in fragments by OpenRouter)
                        if "tool_calls" in delta:
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in current_tool_calls:
                                    current_tool_calls[idx] = {
                                        "id": tc.get("id", ""),
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    }
                                if tc.get("id"):
                                    current_tool_calls[idx]["id"] = tc["id"]
                                func = tc.get("function", {})
                                if func.get("name"):
                                    current_tool_calls[idx]["function"]["name"] = func["name"]
                                if func.get("arguments"):
                                    current_tool_calls[idx]["function"]["arguments"] += func["arguments"]
                    except json.JSONDecodeError:
                        continue

                # Yield completed tool calls after stream ends
                for idx in sorted(current_tool_calls.keys()):
                    tc = current_tool_calls[idx]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    yield {
                        "type": "tool_call",
                        "id": tc.get("id", ""),
                        "name": tc["function"]["name"],
                        "arguments": args,
                    }

    def get_conversation_history(self) -> List[Dict]:
        """Get full conversation history."""
        return [msg.to_dict() for msg in self.messages]

    def get_steps(self) -> List[Dict]:
        """Get all ReAct steps taken."""
        return [step.to_dict() for step in self.steps]

    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation."""
        return f"Conversation has {len(self.messages)} messages, {len(self.steps)} tool steps"

    def clear_history(self):
        """Clear conversation history and steps."""
        self.messages = []
        self.steps = []
        logger.info("Session cleared")


# Convenience function
def create_katy_agent(
    user_id: Optional[str] = None,
    user_context: Optional[Dict] = None,
    model: Optional[str] = None,
) -> KatyPMAgent:
    """Create a new Katy PM agent instance."""
    return KatyPMAgent(user_id=user_id, user_context=user_context, model=model)
