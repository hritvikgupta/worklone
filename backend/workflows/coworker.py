"""
Co-Worker — Workflow Executor Agent (True ReAct)

A TRUE autonomous ReAct agent that executes workflows step-by-step.
No hardcoded loops, no max iterations, no regex parsing.
The LLM decides everything via native function calling.

When a workflow is scheduled, this agent:
- Reads the workflow definition
- Executes each block in order using the right tools
- Resolves variables between blocks ({{block.output.field}})
- Handles conditions, loops, and errors
- Saves execution results
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

# Import all tools available to the executor
from backend.product_manager.tools.jira_tool import JiraTool
from backend.product_manager.tools.notion_tool import NotionTool
from backend.product_manager.tools.analytics_tool import AnalyticsTool
from backend.product_manager.tools.research_tool import ResearchTool
from backend.product_manager.tools.github_tool import GitHubTool

logger = get_logger("coworker")


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


COWORKER_SYSTEM_PROMPT = """Your name is Harry. You are a Workflow Executor Agent — an AI agent that executes automated workflows step-by-step.

## Who You Are
You are Harry — a precise, reliable workflow executor. You are NOT a conversational chatbot. You are an automation engine with reasoning. When a workflow is triggered, you execute it block by block, using tools, resolving variables, and saving results.

## What A Workflow Looks Like

A workflow has blocks connected in sequence or with conditions:
- **trigger**: What started this workflow (schedule, webhook, manual, API)
- **tool**: Call a tool (GitHub, Slack, Gmail, Jira, Notion, LLM, HTTP, Function, etc.)
- **agent**: Call an LLM with a prompt and system prompt
- **function**: Run Python code
- **http**: Make an HTTP request
- **condition**: Branch based on a value (if/else)
- **variable**: Set a workflow variable
- **end**: Workflow complete

Each block has:
- `id`: Unique identifier (e.g., "block_abc123")
- `config`: What the block does (tool name, action, params, prompt, etc.)
- `inputs`: Data coming from previous blocks
- `outputs`: Data this block produces (used by later blocks)

## How You Execute Workflows

1. **READ** the workflow definition and understand all blocks and their connections
2. **START** from the first block (usually a trigger or start block)
3. **RESOLVE** any variable references like `{{block_1.output.issues}}` using previous block outputs
4. **EXECUTE** the block by calling the appropriate tool with resolved parameters
5. **SAVE** the output so later blocks can reference it
6. **FOLLOW** the connections to the next block
7. **HANDLE CONDITIONS**: If a condition block says "if X, go to block A, else block B" — evaluate and follow the right path
8. **REPEAT** until you reach the end block
9. **REPORT** the final results and mark the workflow as complete

## Available Tools

You have access to these tools:
- **github**: List repos, issues, PRs, create issues, get repo info
- **jira**: Manage backlog, create issues, track sprints
- **notion**: Write docs, PRDs, roadmaps
- **slack_send**: Send messages to Slack channels
- **gmail**: Read and send emails
- **http_request**: Make HTTP requests to any API
- **call_llm**: Call an LLM for summarization, analysis, or generation
- **run_function**: Execute Python code
- **analytics**: Fetch product metrics
- **research**: Market research, competitor analysis

## Execution Rules

1. **Execute blocks in order** — follow the workflow connections
2. **Resolve variables** — replace `{{block_id.output.field}}` with actual values from previous outputs
3. **Handle failures** — if a tool fails, note it and either retry or skip based on the workflow config
4. **Save outputs** — every block's output must be saved so later blocks can use it
5. **Be efficient** — don't overthink. Execute what the workflow says.
6. **No conversation** — you are an executor, not a chatbot. Return only execution results.

## Output Format

After executing the workflow, provide:
1. **Summary**: What workflow ran, how many blocks executed
2. **Results**: Key outputs from each block
3. **Status**: Success or failed (with error details if failed)

## Integration Protocol

- If a tool requires credentials that are missing, log the error and continue to the next block
- If the workflow has a condition that cannot be evaluated, log a warning and follow the "else" path
- Always save execution results to the database

Current date: {current_date}
Workflow: {workflow_name}
Trigger: {trigger_info}
User: {user_name}
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


class CoWorkerAgent:
    """
    Harry — Autonomous Workflow Executor Agent.

    Executes workflows step-by-step using ReAct pattern:
    - Reads workflow definition from DB
    - Resolves variables between blocks
    - Calls tools (GitHub, Slack, LLM, etc.) for each block
    - Handles conditions, loops, errors
    - Saves execution results

    NO LOOPS WITH LIMITS. NO KEYWORD MATCHING. NO REGEX PARSING.
    The LLM is in full control via native function calling.
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

        # Session context — full conversation history
        self.messages: List[ContextMessage] = []
        self.steps: List[ReActStep] = []

        # OpenRouter config
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

        # Register all tools
        self._register_tools()

        logger.info(f"Co-Worker Executor initialized for user: {self.user_id}")

    def _register_tools(self):
        """Register all available tools for workflow execution."""
        # Communication tools
        self.tool_registry.register(SlackTool())
        self.tool_registry.register(GmailTool())
        self.tool_registry.register(HTTPTool())
        self.tool_registry.register(FunctionTool())

        # Integration tools
        self.tool_registry.register(JiraTool())
        self.tool_registry.register(NotionTool())
        self.tool_registry.register(AnalyticsTool())
        self.tool_registry.register(ResearchTool())
        self.tool_registry.register(GitHubTool())

        logger.info(f"Registered {len(self.tool_registry.list_names())} tools")

    async def execute_workflow(
        self,
        workflow_id: str,
        stream: bool = True,
        emit_events: bool = False,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Execute a workflow from the database.

        Flow:
        1. Load workflow definition from DB
        2. Build execution context (blocks, connections, previous outputs)
        3. Send to LLM with tools → LLM executes block by block via function calling
        4. Save results, mark workflow complete

        The LLM is in full control. No hardcoded DAG, no iteration caps.
        """
        logger.info(f"Executing workflow: {workflow_id}")

        # Load workflow from DB
        try:
            workflow = self.store.get_workflow(workflow_id)
            if not workflow:
                yield {"type": "error", "message": f"Workflow {workflow_id} not found"}
                return
        except Exception as e:
            yield {"type": "error", "message": f"Failed to load workflow: {str(e)}"}
            return

        # Build execution context
        blocks = self.store.get_blocks_for_workflow(workflow_id)
        connections = self.store.get_connections_for_workflow(workflow_id)
        trigger = self.store.get_trigger_for_workflow(workflow_id)

        # Build workflow definition as a readable string for the LLM
        workflow_def = self._format_workflow_definition(workflow, blocks, connections, trigger)

        # Add execution instruction as the user message
        exec_message = f"""Execute this workflow now. Follow the blocks in order, resolve any variables, call the right tools, and save outputs.

Workflow Definition:
{workflow_def}

Start executing from the first non-trigger block. Resolve all variable references like {{{{block_id.output.field}}}}. Report final results when done."""

        self.messages.append(ContextMessage(role="user", content=exec_message))

        # Build system prompt
        user_name = self.user_context.get("name", "Anonymous")
        trigger_info = trigger.get("name", "manual") if trigger else "manual"
        system_prompt = COWORKER_SYSTEM_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            workflow_name=workflow.get("name", "unknown"),
            trigger_info=trigger_info,
            user_name=user_name,
        )

        # Build messages array
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Get tools in OpenAI function-calling format
        tools = self.tool_registry.to_openai_tools()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}[Harry] EXECUTING WORKFLOW: {workflow.get('name', workflow_id)}{Colors.ENDC}")
        print(f"{Colors.CYAN}Trigger: {trigger_info}{Colors.ENDC}")
        print(f"{Colors.BLUE}[Harry] Tools available: {self.tool_registry.list_names()}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")

        cycle_count = 0

        # === AUTONOMOUS ReAct LOOP ===
        while True:
            cycle_count += 1
            print(f"\n{Colors.YELLOW}{'─' * 50}{Colors.ENDC}")
            print(f"{Colors.YELLOW}[Harry] CYCLE {cycle_count}{Colors.ENDC}")
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
                logger.exception(f"[Harry] LLM error: {e}")
                if stream and emit_events:
                    yield {"type": "error", "message": str(e)}
                elif stream:
                    yield f"\n[Error: {str(e)}]\n"
                return

            print(f"\n{Colors.GREEN}[Harry] Response ({len(response_text)} chars){Colors.ENDC}")
            print(f"{Colors.GREEN}{response_text[:500]}{'...' if len(response_text) > 500 else ''}{Colors.ENDC}")

            # Store assistant message
            if response_text.strip():
                self.messages.append(ContextMessage(role="assistant", content=response_text.strip()))

            # === AGENT DECIDES: DONE OR CONTINUE? ===
            if not tool_calls:
                print(f"\n{Colors.BOLD}{Colors.GREEN}[Harry] EXECUTION COMPLETE{Colors.ENDC}")

                # Mark workflow as completed in DB
                try:
                    self.store.update_workflow_status(workflow_id, "completed")
                except Exception as e:
                    logger.warning(f"Failed to update workflow status: {e}")

                if stream and emit_events:
                    yield {"type": "final", "content": response_text.strip()}
                return

            # === TOOL CALLS — EXECUTE THEM ===
            print(f"\n{Colors.BOLD}{Colors.YELLOW}[Harry] TOOL CALLS: {len(tool_calls)}{Colors.ENDC}")

            # Build assistant message with tool_calls
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

                print(f"\n{Colors.YELLOW}[Harry] Tool #{i + 1}: {tool_name}{Colors.ENDC}")
                print(f"{Colors.YELLOW}  Input: {json.dumps(tool_input, indent=2)}{Colors.ENDC}")

                if stream and emit_events:
                    yield {
                        "type": "tool_start",
                        "cycle": cycle_count,
                        "tool": tool_name,
                        "input": tool_input,
                    }
                elif stream:
                    yield f"\n🔧 {tool_name}...\n"

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

                # Append tool result in OpenAI format
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation,
                })

            print(f"\n{Colors.CYAN}[Harry] Continuing to next cycle...{Colors.ENDC}")

    def _format_workflow_definition(self, workflow, blocks, connections, trigger) -> str:
        """Format workflow definition as a readable string for the LLM."""
        lines = []
        lines.append(f"Name: {workflow.get('name', 'unknown')}")
        lines.append(f"Description: {workflow.get('description', '')}")
        lines.append(f"Trigger: {json.dumps(trigger) if trigger else 'manual'}")
        lines.append("")
        lines.append(f"Blocks ({len(blocks)}):")

        for block in blocks:
            lines.append(f"  - ID: {block['id']}")
            lines.append(f"    Type: {block.get('block_type', 'unknown')}")
            lines.append(f"    Config: {json.dumps(block.get('config', {}))}")
            lines.append(f"    Inputs: {json.dumps(block.get('inputs', {}))}")
            lines.append("")

        lines.append(f"Connections ({len(connections)}):")
        for conn in connections:
            lines.append(f"  {conn['from_block_id']} → {conn['to_block_id']}")

        return "\n".join(lines)

    async def _stream_llm(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream response from LLM via OpenRouter with native function calling.
        """
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not set")
            yield {"type": "error", "message": "OPENROUTER_API_KEY not set"}
            return

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # Lower temperature for more deterministic execution
            "max_tokens": 4096,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        print(f"{Colors.CYAN}[LLM] Model: {self.model} | Messages: {len(messages)} | Tools: {len(tools) if tools else 0}{Colors.ENDC}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ceo-agent.local",
                    "X-Title": "CEO Agent - Harry Workflow Executor",
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

                        if "content" in delta and delta["content"]:
                            yield {"type": "content", "token": delta["content"]}

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

    def get_steps(self) -> List[Dict]:
        """Get all ReAct steps taken."""
        return [step.to_dict() for step in self.steps]

    def clear_history(self):
        """Clear conversation history and steps."""
        self.messages = []
        self.steps = []


# Convenience function
def create_coworker_agent(
    user_id: Optional[str] = None,
    user_context: Optional[Dict] = None,
    model: Optional[str] = None,
) -> CoWorkerAgent:
    """Create a new Co-Worker Executor agent instance."""
    return CoWorkerAgent(user_id=user_id, user_context=user_context, model=model)
