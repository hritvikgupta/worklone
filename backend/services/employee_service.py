"""Service layer for DB-configured generic employees."""

import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv

from backend.employee.react_agent import ContextMessage, GenericEmployeeAgent
from backend.store.auth_store import AuthDB

load_dotenv()


class EmployeeService:
    """Service wrapper for generic employee ReAct agents."""

    def __init__(self):
        self.agents: dict[str, GenericEmployeeAgent] = {}
        self.user_models: dict[str, str] = {}
        self.db = AuthDB()

    def _agent_key(self, employee_id: str, user_id: str, session_id: Optional[str]) -> str:
        return f"{employee_id}:{user_id}:{session_id or 'default'}"

    def get_cached_agent(self, employee_id: str, user_id: str, session_id: Optional[str] = None) -> Optional[GenericEmployeeAgent]:
        """Get an existing cached agent (for resume). Returns None if not found."""
        key = self._agent_key(employee_id, user_id, session_id)
        return self.agents.get(key)

    def _get_agent(
        self,
        employee_id: str,
        user_id: str = "anonymous",
        owner_id: str = "",
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> GenericEmployeeAgent:
        key = self._agent_key(employee_id, user_id, session_id)
        if key not in self.agents or (model and self.user_models.get(key) != model):
            self.agents[key] = GenericEmployeeAgent(
                employee_id=employee_id,
                user_id=user_id,
                owner_id=owner_id,
                user_context={},
                model=model,
            )
            if model:
                self.user_models[key] = model
        return self.agents[key]

    def _ensure_session_has_employee(self, session_id: str, employee_id: str, user_id: str) -> None:
        """Ensure the session is linked to the correct employee. If the session
        was created without an employee_id (legacy), patch it now."""
        session = self.db.get_chat_session(session_id=session_id, user_id=user_id)
        if session and not session.get("employee_id"):
            conn = self.db._get_conn()
            try:
                conn.execute(
                    "UPDATE chat_sessions SET employee_id = ? WHERE id = ? AND user_id = ?",
                    (employee_id, session_id, user_id),
                )
                conn.commit()
            finally:
                conn.close()

    def _restore_history_if_needed(
        self,
        agent: GenericEmployeeAgent,
        session_id: Optional[str],
        conversation_history: Optional[List[dict]],
    ) -> None:
        if len(agent.messages) > 0:
            return

        if session_id:
            stored_history = self.db.get_chat_history(session_id=session_id, limit=500)
            for msg in stored_history:
                agent.messages.append(ContextMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                ))
            return

        if conversation_history:
            for msg in conversation_history:
                agent.messages.append(ContextMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                ))

    def _update_session_title_if_default(self, session_id: Optional[str], user_input: str) -> None:
        if not session_id:
            return
        session = self.db.get_chat_session(session_id=session_id)
        if not session:
            return
        current_title = (session.get("title") or "").strip()
        if current_title and current_title != "New Chat":
            return
        title = " ".join(user_input.strip().split())
        if len(title) > 80:
            title = f"{title[:77]}..."
        if not title:
            title = "New Chat"
        self.db.update_chat_session(session_id=session_id, title=title)

    async def chat(
        self,
        employee_id: str,
        message: str,
        user_id: str = "anonymous",
        owner_id: str = "",
        conversation_history: Optional[List[dict]] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        agent = self._get_agent(employee_id, user_id, owner_id, model, session_id=session_id)
        self._restore_history_if_needed(agent, session_id, conversation_history)
        self._update_session_title_if_default(session_id, message)

        if session_id:
            self._ensure_session_has_employee(session_id, employee_id, user_id)
        if session_id:
            self.db.save_message(session_id=session_id, role="user", content=message, model=model)

        full_response = ""
        async for chunk in agent.chat(message, stream=True):
            clean_chunk = re.sub(r'\x1b\[[0-9;]*m', '', chunk)
            full_response += clean_chunk

        final_response = full_response.strip()
        if session_id and final_response:
            self.db.save_message(
                session_id=session_id,
                role="assistant",
                content=final_response,
                model=model,
            )
        return final_response

    async def chat_stream(
        self,
        employee_id: str,
        message: str,
        user_id: str = "anonymous",
        owner_id: str = "",
        conversation_history: Optional[List[dict]] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        agent = self._get_agent(employee_id, user_id, owner_id, model, session_id=session_id)
        self._restore_history_if_needed(agent, session_id, conversation_history)
        self._update_session_title_if_default(session_id, message)

        if session_id:
            self._ensure_session_has_employee(session_id, employee_id, user_id)
        if session_id:
            self.db.save_message(session_id=session_id, role="user", content=message, model=model)

        final_response = ""
        thinking_parts: list[str] = []

        async for event in agent.chat(message, stream=True, emit_events=True):
            if isinstance(event, str):
                clean_chunk = re.sub(r'\x1b\[[0-9;]*m', '', event)
                if clean_chunk.strip():
                    thinking_parts.append(clean_chunk)
                yield {"type": "thinking", "content": clean_chunk}
                continue

            sanitized_event = dict(event)
            for key in ("content", "output", "message", "token"):
                value = sanitized_event.get(key)
                if isinstance(value, str):
                    sanitized_event[key] = re.sub(r'\x1b\[[0-9;]*m', '', value)

            if sanitized_event.get("type") == "thinking":
                content = str(sanitized_event.get("content") or "")
                if content.strip():
                    thinking_parts.append(content)
            elif sanitized_event.get("type") == "tool_result":
                output = str(sanitized_event.get("output") or "")
                if output.strip():
                    thinking_parts.append(output)
            elif sanitized_event.get("type") == "final":
                final_response = str(sanitized_event.get("content") or "").strip()

            yield sanitized_event

        if session_id and final_response:
            thinking = "\n\n".join(part.strip() for part in thinking_parts if part.strip()) or None
            self.db.save_message(
                session_id=session_id,
                role="assistant",
                content=final_response,
                model=model,
                thinking=thinking,
            )
