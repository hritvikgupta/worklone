"""
Katy Service - Service layer for Katy PM Agent interactions
"""

import os
import re
import sys
from typing import List, Optional, AsyncGenerator, Dict, Any
from dotenv import load_dotenv

from backend.product_manager.katy import KatyPMAgent
from backend.store.auth_store import AuthDB

load_dotenv()


class KatyService:
    """Service for interacting with Katy PM Agent"""

    def __init__(self):
        """Initialize the Katy service"""
        self.agents = {}  # Cache agents by user_id + session_id
        self.user_models = {}  # Store model preference by user_id + session_id
        self.db = AuthDB()

    def _agent_key(self, user_id: str, session_id: Optional[str]) -> str:
        return f"{user_id}:{session_id or 'default'}"

    def _get_agent(self, user_id: str = "anonymous", model: Optional[str] = None, session_id: Optional[str] = None) -> KatyPMAgent:
        """Get or create a Katy agent for a user"""
        key = self._agent_key(user_id, session_id)
        if key not in self.agents or (model and self.user_models.get(key) != model):
            self.agents[key] = KatyPMAgent(
                user_id=user_id,
                user_context={},
                model=model
            )
            if model:
                self.user_models[key] = model
        return self.agents[key]

    def _restore_history_if_needed(self, agent: KatyPMAgent, session_id: Optional[str], conversation_history: Optional[List[dict]]):
        """Restore session history into a fresh agent instance."""
        if len(agent.messages) > 0:
            return

        from backend.product_manager.katy import ContextMessage

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

    def _update_session_title_if_default(self, session_id: Optional[str], user_input: str):
        """Set a meaningful title from the first user message."""
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
        message: str,
        user_id: str = "anonymous",
        conversation_history: Optional[List[dict]] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Send a message to Katy and get a complete response.

        The agent maintains its own session history internally.
        conversation_history from the client is used to restore context
        if this is a fresh agent instance.
        """
        agent = self._get_agent(user_id, model, session_id=session_id)
        self._restore_history_if_needed(agent, session_id, conversation_history)
        self._update_session_title_if_default(session_id, message)

        if session_id:
            self.db.save_message(session_id=session_id, role="user", content=message, model=model)

        # Collect full response from streaming
        full_response = ""
        async for chunk in agent.chat(message, stream=True):
            # Strip ANSI color codes
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
        message: str,
        user_id: str = "anonymous",
        conversation_history: Optional[List[dict]] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream Katy's response.

        The agent maintains its own session history internally.
        """
        agent = self._get_agent(user_id, model, session_id=session_id)
        self._restore_history_if_needed(agent, session_id, conversation_history)
        self._update_session_title_if_default(session_id, message)

        if session_id:
            self.db.save_message(session_id=session_id, role="user", content=message, model=model)

        final_response = ""
        thinking_parts: list[str] = []

        # Stream structured events
        async for event in agent.chat(message, stream=True, emit_events=True):
            if isinstance(event, str):
                clean_chunk = re.sub(r'\x1b\[[0-9;]*m', '', event)
                if clean_chunk.strip():
                    thinking_parts.append(clean_chunk)
                yield {"type": "thinking", "content": clean_chunk}
                continue

            sanitized_event = dict(event)
            for key in ("content", "output", "message"):
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
