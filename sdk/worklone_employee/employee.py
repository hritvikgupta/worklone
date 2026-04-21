"""
Employee — the main SDK entry point.
"""

import asyncio
import hashlib
import inspect
import os
from pathlib import Path
from typing import Optional, AsyncGenerator, List

from worklone_employee.tools.base import BaseTool, ToolResult


class FunctionToolAdapter(BaseTool):
    """Wraps a plain Python function as a BaseTool."""

    def __init__(self, fn, description: str = "", name: str = ""):
        self.fn = fn
        self.name = name or fn.__name__
        self.description = description or fn.__doc__ or self.name
        self.category = "custom"

    def get_schema(self) -> dict:
        sig = inspect.signature(self.fn)
        properties = {}
        required = []
        type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
        for param_name, param in sig.parameters.items():
            annotation = param.annotation
            json_type = type_map.get(annotation, "string")
            properties[param_name] = {"type": json_type}
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        return {"type": "object", "properties": properties, "required": required}

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            if inspect.iscoroutinefunction(self.fn):
                result = await self.fn(**parameters)
            else:
                result = self.fn(**parameters)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class Employee:
    """
    Create an autonomous AI employee.

    Usage:
        emp = Employee(name="Aria", model="anthropic/claude-haiku-4-5", owner_id="user_alice")
        emp.use_tools(["web_search"])
        emp.add_skill("financial analysis", category="finance", proficiency_level=90)
        emp.enable_evolution()
        response = emp.run("What is the price of NVDA?")

    DB stores ONLY:
        - Chat session history  (if session_id is set)
        - User memory           (evolution, per owner_id)
        - Learned skills        (evolution, per owner_id)
    Everything else — name, model, system_prompt, static skills — lives in memory only.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        model: str = "openai/gpt-4o",
        temperature: float = 0.7,
        system_prompt: str = "",
        db: Optional[str] = None,
        owner_id: str = "sdk_user",
        session_id: Optional[str] = None,
        auto_approve: bool = False,
    ):
        self._setup_db(db)

        self._name = name
        self._description = description
        self._model = model
        self._temperature = temperature
        self._system_prompt = system_prompt
        self._owner_id = owner_id
        self._session_id = session_id
        self._auto_approve = auto_approve
        self._on_approval_needed = None   # optional callback set via .on_approval_needed()

        # Deterministic ID — same name+owner always maps to same evolution bucket
        emp_hash = hashlib.md5(f"{owner_id}:{name}".encode()).hexdigest()[:12]
        self._employee_id = f"sdk_{emp_hash}"

        self._catalog_tool_names: List[str] = []
        self._static_skills: List = []          # EmployeeSkill objects (in-memory only)
        self._custom_tools: List[BaseTool] = []
        self._agent = None
        self._evolution_enabled = False

    def _setup_db(self, db_path: Optional[str]) -> None:
        if db_path:
            resolved = str(Path(db_path).expanduser().resolve())
        else:
            resolved = str(Path.home() / ".worklone" / "sdk.db")
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        os.environ["APP_DB"] = resolved

    def _get_session_store(self):
        from worklone_employee.db.store import EmployeeStore
        return EmployeeStore()

    def use_tools(self, tool_names: List[str]) -> "Employee":
        """Enable built-in catalog tools by name (e.g. ['web_search', 'http_request'])."""
        for name in tool_names:
            if name not in self._catalog_tool_names:
                self._catalog_tool_names.append(name)
        self._agent = None
        return self

    def tool(self, description: str = "", name: str = None):
        """Decorator to register a plain Python function as a tool."""
        def decorator(fn):
            adapter = FunctionToolAdapter(fn=fn, description=description, name=name or fn.__name__)
            self._custom_tools.append(adapter)
            if self._agent:
                self._agent.tool_registry.register(adapter)
            return fn
        return decorator

    def add_tool(self, tool_instance: BaseTool) -> "Employee":
        """Add a pre-built BaseTool instance."""
        self._custom_tools.append(tool_instance)
        if self._agent:
            self._agent.tool_registry.register(tool_instance)
        return self

    def add_skill(
        self,
        skill_name: str,
        category: str = "research",
        proficiency_level: int = 80,
        description: str = "",
    ) -> "Employee":
        """Assign a static skill (injected into system prompt).

        Args:
            skill_name: e.g. "financial analysis", "copywriting"
            category: research/coding/devops/analytics/communication/product/design/sales/finance
            proficiency_level: 0-100
            description: optional extra context for the LLM
        """
        from worklone_employee.types import EmployeeSkill, SkillCategory
        from worklone_employee.workflows.utils import generate_id

        existing = {s.skill_name for s in self._static_skills}
        if skill_name not in existing:
            try:
                cat = SkillCategory(category.lower())
            except ValueError:
                cat = SkillCategory.RESEARCH
            self._static_skills.append(EmployeeSkill(
                id=generate_id("esk"),
                employee_id=self._employee_id,
                skill_name=skill_name,
                category=cat,
                proficiency_level=proficiency_level,
                description=description,
            ))
        self._agent = None
        return self

    def on_approval_needed(self, callback) -> "Employee":
        """Register a callback for when the agent needs human approval.

        The callback receives the event dict and must return a dict:
            {"approved": True/False, "message": "optional reason"}

        Example:
            @emp.on_approval_needed
            def handle(event):
                print(event["message"])
                answer = input("Approve? (y/n): ")
                return {"approved": answer.lower() == "y", "message": ""}
        """
        self._on_approval_needed = callback
        return self

    def enable_evolution(self) -> "Employee":
        """Enable memory + skill learning persisted across sessions."""
        self._evolution_enabled = True
        if self._agent:
            self._agent._turns_since_memory_review = 0
            self._agent._tool_iters_since_skill_review = 0
        return self

    def _ensure_agent(self):
        if self._agent is not None:
            return
        from worklone_employee.agents.react_agent import GenericEmployeeAgent, ContextMessage

        self._agent = GenericEmployeeAgent(
            employee_id=self._employee_id,
            user_id=self._owner_id,
            owner_id=self._owner_id,
            name=self._name,
            role=self._description or self._name,
            description=self._description,
            system_prompt=self._system_prompt,
            model=self._model,
            temperature=self._temperature,
            skills=self._static_skills,
            extra_tool_names=self._catalog_tool_names,
        )

        for tool in self._custom_tools:
            self._agent.tool_registry.register(tool)

        if not self._evolution_enabled:
            self._agent._turns_since_memory_review = -(2 ** 30)
            self._agent._tool_iters_since_skill_review = -(2 ** 30)

        # Restore chat history from DB if session_id provided
        if self._session_id and not self._agent.messages:
            store = self._get_session_store()
            for msg in store.get_chat_history(self._session_id):
                self._agent.messages.append(ContextMessage(
                    role=msg["role"], content=msg["content"]
                ))

    def run(self, message: str) -> str:
        """Run the employee synchronously. Returns the final response string."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError(
                "emp.run() cannot be called inside a running event loop. "
                "Use 'await emp._arun(message)' or 'async for token in emp.stream(message)' instead."
            )
        return asyncio.run(self._arun(message))

    async def _arun(self, message: str) -> str:
        self._ensure_agent()

        if self._session_id:
            store = self._get_session_store()
            session = store.get_chat_session(self._session_id)
            if not session:
                store.create_chat_session(
                    user_id=self._owner_id,
                    employee_id=self._employee_id,
                    model=self._model,
                )
                session = store.get_chat_session(self._session_id)
            if session and (not session.get("title") or session["title"] == "New Chat"):
                store.update_chat_session(self._session_id, title=message.strip()[:80])
            store.save_message(self._session_id, "user", message, model=self._model)

        final = ""
        collected = []
        async for event in self._agent.chat(message, stream=True, emit_events=True, auto_approve_human=self._auto_approve):
            if not isinstance(event, dict):
                continue
            t = event.get("type")
            if t == "content_token":
                collected.append(event.get("token", ""))
            elif t == "final":
                final = event.get("content", "".join(collected))
                break
            elif t == "confirmation_required":
                if self._on_approval_needed:
                    response = self._on_approval_needed(event)
                else:
                    # Default: print to stdout, read from stdin
                    print(f"\n[approval needed] {event.get('message', 'Approve?')}")
                    answer = input("Approve? (y/n): ").strip().lower()
                    response = {"approved": answer == "y", "message": ""}
                self._agent.resume_with_user_response(response)
        if not final:
            final = "".join(collected)

        if self._session_id and final:
            store = self._get_session_store()
            store.save_message(self._session_id, "assistant", final, model=self._model)

        return final

    async def stream(self, message: str) -> AsyncGenerator[str, None]:
        """Stream the employee's response token by token.

        Yields content tokens as strings. If the agent pauses for approval,
        the registered on_approval_needed callback is called (or stdin prompt used).
        """
        self._ensure_agent()
        async for event in self._agent.chat(message, stream=True, emit_events=True, auto_approve_human=self._auto_approve):
            if not isinstance(event, dict):
                continue
            t = event.get("type")
            if t == "content_token":
                yield event.get("token", "")
            elif t == "confirmation_required":
                if self._on_approval_needed:
                    response = self._on_approval_needed(event)
                else:
                    print(f"\n[approval needed] {event.get('message', 'Approve?')}")
                    answer = input("Approve? (y/n): ").strip().lower()
                    response = {"approved": answer == "y", "message": ""}
                self._agent.resume_with_user_response(response)

    def reset(self) -> "Employee":
        """Clear in-memory conversation history. Keeps evolution data in DB."""
        if self._agent:
            self._agent.messages = []
        return self
