"""
Co-Worker — Workflow Executor Agent (True ReAct)

A copy of GenericEmployeeAgent's ReAct loop, but:
- No DB loading — identity/prompt is hardcoded like Katy
- ALL tools from catalog (not selective)
- Same _tool_context with user_id so OAuth works
- Same _stream_llm, same tool execution, same everything
"""

import json
import os
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from backend.services.llm_config import get_provider_config, detect_provider, get_headers, get_payload_extras
from backend.tools.catalog import create_all_tools
from backend.tools.system_tools.registry import ToolRegistry
from backend.store.workflow_store import WorkflowStore
from backend.workflows.types import WorkflowTaskStatus, WorkflowStatus
from backend.workflows.logger import get_logger

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


COWORKER_SYSTEM_PROMPT = """Your name is Harry. You are a Workflow Execution Specialist — an AI employee who thinks strategically, operates autonomously, and drives high-quality outcomes by executing automated workflows step-by-step.

## Identity & Working Style
You are Harry, a precise, reliable, and methodical workflow execution specialist. You approach every workflow with careful analysis, execute each task thoroughly using the right tools, and deliver real, tangible results. You are proactive about handling edge cases, transparent about failures, and always focused on completing the mission. You never simulate or pretend — you call real tools and produce real outputs.

## Core Responsibilities

### 1. Sequential Workflow Execution
- Read and understand the full workflow definition before starting
- Execute each task in order, one by one, using the appropriate tools
- Pass data between tasks — if Task 2 depends on Task 1's output, use the actual data received
- Track progress and report status for each completed task

### 2. Tool-Based Task Resolution
- For every task, identify and call the correct tool to accomplish it
- Never describe what you would do — actually DO it by calling the tool
- Use tool results as real data for subsequent tasks

### 3. Error Handling & Recovery
- If a tool fails, note the error and attempt an alternative approach
- If credentials are missing, report it clearly in the task result and move on
- Never let one failed task silently block the entire workflow
- Retry with adjusted parameters when appropriate

### 4. Cross-System Integration
- Coordinate across multiple external systems (Gmail, Slack, Notion, GitHub, Jira, etc.)
- Chain outputs from one system as inputs to another
- Respect rate limits and API constraints
- Handle authentication transparently

### 5. Results Reporting
- Provide clear, structured results for each completed task
- Summarize the overall workflow outcome when all tasks finish
- Include relevant data, links, and artifacts produced during execution
- Report failures with enough detail to diagnose the issue

## Domain Expertise
- Multi-system automation and orchestration
- API-based task execution across SaaS platforms
- Data transformation and pipeline execution
- Error recovery and graceful degradation strategies

## Operating Principles
- Always call the real tool — never simulate, fabricate, or describe what you would do
- Execute tasks in the exact order specified by the workflow
- Be efficient — don't overthink, execute exactly what the workflow says
- If a tool returns data, use that actual data in subsequent steps
- Report failures honestly rather than masking them

## Tool Access
You have access to all tools in the system. Use them to accomplish tasks.

Available tools:
{tools_text}

## Integration Protocol

Before using external tools (Jira, Notion, GitHub, Slack, Gmail, analytics systems, or other integrations):
1. Just try to use the tool directly — credentials are pre-configured for the user
2. If a tool returns an authentication error, note it in the task result and move on
3. Do NOT ask the user for credentials — you are an automated executor

## How You Work (ReAct Pattern)

You follow the ReAct pattern to solve problems autonomously:

1. **THINK** - Reason about the current task and what tool to use
2. **ACT** - Call the appropriate tool with the right parameters
3. **OBSERVE** - Process the results and update your understanding
4. **REPEAT** - Continue until all workflow tasks are completed

You decide when to use tools and when to report results. YOU are in control.

## Important Guidelines

- Always think through what tool to use for each task
- Use tools when you need to perform actions or gather information
- Be transparent about your reasoning process
- If a tool fails, try alternative approaches
- Provide clear results for each completed task
- Do not ask clarifying questions — you are an automated executor, not a chatbot

## Response Style

1. **Think out loud**: Share your reasoning when deciding which tool to use
2. **Be efficient**: Execute the task, report the result, move on
3. **Use data**: Reference actual tool outputs, not hypothetical results
4. **Be concise**: Report results clearly without unnecessary verbosity

Current date: {current_date}
Workflow: {workflow_name}
Trigger: {trigger_info}
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

    Exact copy of GenericEmployeeAgent's ReAct loop, but:
    - No DB loading — identity is hardcoded (like Katy)
    - ALL tools from catalog
    - Same _tool_context with user_id so OAuth/credentials resolve
    - Same _stream_llm, same tool execution flow
    """

    def __init__(
        self,
        owner_id: str,
        model: str = "moonshotai/kimi-k2.5",
    ):
        self.owner_id = owner_id
        self.user_id = owner_id  # owner IS the user — needed for OAuth
        self.model = model
        self.tool_registry = ToolRegistry()
        self.store = WorkflowStore()

        # Session context — full conversation history
        self.messages: List[ContextMessage] = []
        self.steps: List[ReActStep] = []

        # LLM provider config from centralized service
        self.provider_name = detect_provider(self.model)
        llm_config = get_provider_config(self.model)
        self.api_key = llm_config["api_key"]
        self.base_url = llm_config["base_url"]

        # Register ALL tools from catalog
        self._register_tools()

        logger.info(f"Co-Worker Agent initialized for owner: {self.owner_id}")

    def _register_tools(self):
        """Register every tool from the shared catalog — same as Katy."""
        for tool in create_all_tools():
            self.tool_registry.register(tool)
        logger.info(f"Registered {len(self.tool_registry.list_names())} tools")

    def _tool_context(self, tool_name: str) -> Dict[str, Any]:
        """
        Build tool context — same pattern as GenericEmployeeAgent._tool_context.
        CRITICAL: user_id must be set so OAuth resolution finds credentials.
        """
        return {
            "user_id": self.user_id,
            "actor_type": "workflow",
            "actor_id": "harry",
            "actor_name": "Harry",
            "employee_id": "harry",
            "employee_name": "Harry",
            "employee_role": "Workflow Execution Specialist",
            "tool_config": {},
            "tool_configs": {},
        }

    def _tools_text(self) -> str:
        tool_names = self.tool_registry.list_names()
        if not tool_names:
            return "- No tools available"
        return "\n".join(f"- {name}" for name in tool_names)

    def _build_system_prompt(self, workflow_name: str, trigger_info: str) -> str:
        return COWORKER_SYSTEM_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            workflow_name=workflow_name,
            trigger_info=trigger_info,
            tools_text=self._tools_text(),
        )

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_input: dict = None,
        stream: bool = True,
        emit_events: bool = False,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Execute a sequential task workflow autonomously using the ReAct loop.
        Exact same flow as GenericEmployeeAgent.chat().
        """
        logger.info(f"Executing workflow: {workflow_id}")

        try:
            workflow = self.store.get_workflow(workflow_id, self.owner_id)
            if not workflow:
                yield {"type": "error", "message": f"Workflow {workflow_id} not found"}
                return
        except Exception as e:
            yield {"type": "error", "message": f"Failed to load workflow: {str(e)}"}
            return

        trigger_info = "manual"
        if trigger_input:
            trigger_info = f"manual with input: {json.dumps(trigger_input)}"
        elif workflow.triggers:
            t = workflow.triggers[0]
            trigger_info = f"{t.trigger_type.value} trigger"

        # Build workflow definition for LLM
        lines = []
        lines.append(f"Name: {workflow.name}")
        lines.append(f"Description: {workflow.description}")
        lines.append(f"Tasks to Execute ({len(workflow.tasks)}):")
        for i, task in enumerate(workflow.tasks):
            lines.append(f"  {i+1}. {task.description}")
        workflow_def = "\n".join(lines)

        exec_message = f"""Execute this workflow now. Complete every task in order by ACTUALLY CALLING the appropriate tools.

Workflow Definition:
{workflow_def}

Start executing the tasks now. For each task, call the real tools. Report final results when completely done."""

        # Add user message to session history
        self.messages.append(ContextMessage(role="user", content=exec_message))

        # Build system prompt
        system_prompt = self._build_system_prompt(workflow.name, trigger_info)

        # Build messages array in OpenAI format — full conversation history
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Get tools in OpenAI function-calling format
        tools = self.tool_registry.to_openai_tools()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}[Harry] EXECUTING WORKFLOW: {workflow.name}{Colors.ENDC}")
        print(f"{Colors.CYAN}Trigger: {trigger_info}{Colors.ENDC}")
        print(f"{Colors.BLUE}[Harry] Tools available: {self.tool_registry.list_names()}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")

        # Initialize tasks: first is running, rest are pending
        for i, task in enumerate(workflow.tasks):
            task.status = WorkflowTaskStatus.RUNNING if i == 0 else WorkflowTaskStatus.PENDING
            task.result = ""
            task.error = ""
        self.store.save_workflow(workflow)

        cycle_count = 0
        final_result_text = ""
        failed = False
        current_task_idx = 0

        # === AUTONOMOUS ReAct LOOP ===
        # No iteration limit. The LLM decides when to stop.
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
                        failed = True
                        final_result_text = f"Failed during LLM call: {chunk.get('message', 'Unknown error')}"
                        break
                if failed:
                    break
            except Exception as e:
                logger.exception(f"[Harry] LLM error: {e}")
                failed = True
                final_result_text = f"LLM Exception: {str(e)}"
                break

            print(f"\n{Colors.GREEN}[Harry] LLM Response ({len(response_text)} chars){Colors.ENDC}")
            print(f"{Colors.GREEN}{response_text[:500]}{'...' if len(response_text) > 500 else ''}{Colors.ENDC}")

            # Store assistant message in session context
            if response_text.strip():
                self.messages.append(ContextMessage(role="assistant", content=response_text.strip()))

            # === AGENT DECIDES: DONE OR CONTINUE? ===
            if not tool_calls:
                print(f"\n{Colors.BOLD}{Colors.GREEN}[Harry] NO TOOL CALLS — FINAL ANSWER{Colors.ENDC}")
                final_result_text = response_text.strip()
                if stream and emit_events:
                    yield {"type": "final", "content": final_result_text}
                break

            # === TOOL CALLS — EXECUTE THEM ===
            print(f"\n{Colors.BOLD}{Colors.YELLOW}[Harry] TOOL CALLS DETECTED: {len(tool_calls)}{Colors.ENDC}")
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

            # Execute each tool — same as GenericEmployeeAgent
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
                    yield f"\nUsing {tool_name}...\n"

                result_success = False
                try:
                    # Execute via registry — with full tool context (user_id for OAuth)
                    result = await self.tool_registry.execute(
                        tool_name,
                        tool_input,
                        self._tool_context(tool_name),
                    )
                    result_success = result.success
                    observation = result.to_observation()
                except Exception as e:
                    logger.exception(f"[Harry] Tool execution failed: {e}")
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
                    }
                elif stream:
                    yield f"Done: {observation[:200]}{'...' if len(observation) > 200 else ''}\n\n"

                # Track the step
                self.steps.append(ReActStep(
                    step_number=len(self.steps) + 1,
                    thought=response_text.strip(),
                    action=tool_name,
                    action_input=tool_input,
                    observation=observation,
                ))

                # Live Update to DB for frontend visibility
                try:
                    import re
                    # Look for Task N in the response text
                    matches = re.findall(r'(?i)task\s+(\d+)', response_text)
                    if matches:
                        for m in matches:
                            try:
                                idx = int(m) - 1
                                wf_temp = self.store.get_workflow(workflow_id) or self.store.get_workflow(workflow_id, self.owner_id)
                                if wf_temp and 0 <= idx < len(wf_temp.tasks):
                                    current_task_idx = max(current_task_idx, idx)
                            except Exception:
                                pass

                    wf = self.store.get_workflow(workflow_id) or self.store.get_workflow(workflow_id, self.owner_id)
                    if wf and wf.tasks:
                        # Mark earlier tasks as completed
                        for i in range(current_task_idx):
                            if i < len(wf.tasks):
                                if wf.tasks[i].status.value in ("running", "pending"):
                                    wf.tasks[i].status = WorkflowTaskStatus.COMPLETED
                                    # Don't add boilerplate text
                        
                        target_task = wf.tasks[current_task_idx] if current_task_idx < len(wf.tasks) else wf.tasks[-1]
                        if target_task.status.value == "pending":
                            target_task.status = WorkflowTaskStatus.RUNNING
                        
                        target_task.result = (target_task.result or "")
                        if response_text.strip():
                            # Only add unique thoughts
                            thought = response_text.strip()[:100]
                            if thought not in target_task.result:
                                target_task.result += f"• {thought}...\n"
                        
                        tool_log = f"○ {tool_name}"
                        if tool_log not in target_task.result:
                            target_task.result += f"{tool_log}\n"
                        
                        if not result_success:
                            target_task.error = (target_task.error or "") + f"Error: {observation[:200]}\n"
                        self.store.save_workflow(wf)
                except Exception as e:
                    logger.warning(f"[Harry] Failed to live-update workflow tasks: {e}")

                # Append tool result in OpenAI format — LLM sees the observation next cycle
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation,
                })

            print(f"\n{Colors.CYAN}[Harry] Continuing to next cycle...{Colors.ENDC}")
            # Loop continues — LLM will see tool results and decide next

        # Finalize workflow state in DB
        try:
            wf = self.store.get_workflow(workflow_id) or self.store.get_workflow(workflow_id, self.owner_id)
            if wf:
                if failed:
                    wf.status = WorkflowStatus.FAILED
                    for task in wf.tasks:
                        task.status = WorkflowTaskStatus.FAILED
                        task.error = final_result_text
                else:
                    wf.status = WorkflowStatus.ACTIVE
                    for task in wf.tasks:
                        task.status = WorkflowTaskStatus.COMPLETED
                        task.result = "Completed as part of full workflow execution."
                    if wf.tasks:
                        wf.tasks[-1].result = final_result_text
                self.store.save_workflow(wf)
                logger.info(f"Finalized workflow {workflow_id}: tasks={'FAILED' if failed else 'COMPLETED'}")
            else:
                logger.error(f"Could not reload workflow {workflow_id} for finalization")
        except Exception as e:
            logger.exception(f"Failed to finalize workflow {workflow_id}: {e}")

    async def _stream_llm(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream response from LLM — exact copy of GenericEmployeeAgent._stream_llm.
        """
        if not self.api_key:
            logger.error(f"{self.provider_name.upper()}_API_KEY not set")
            yield {"type": "error", "message": f"{self.provider_name.upper()}_API_KEY not set"}
            return

        logger.info(
            f"LLM CALL | Provider: {self.provider_name.upper()} | Model: {self.model} | "
            f"Messages: {len(messages)} | Tools: {len(tools) if tools else 0}"
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True,
        }
        payload.update(get_payload_extras(self.model))

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

    def get_conversation_history(self) -> List[Dict]:
        return [msg.to_dict() for msg in self.messages]

    def get_steps(self) -> List[Dict]:
        return [step.to_dict() for step in self.steps]
