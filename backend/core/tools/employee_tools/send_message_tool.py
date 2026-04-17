"""
SendMessageToCoworkerTool — sends a message to another employee or the human.

When wait_for_reply is true, the tool returns a special AWAIT_COWORKER marker
that the ReAct loop detects. The loop then pauses the current employee, spawns
or wakes the target employee to process the message, waits for the reply, and
injects it back into the sender's conversation.

When wait_for_reply is false, the message is sent fire-and-forget — the
employee continues immediately.
"""

from uuid import uuid4
from datetime import datetime

from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.db.stores.team_store import TeamStore
from backend.core.agents.employee.types import (
    TeamMessage,
    SenderType,
    MessageStatus,
)

AWAIT_COWORKER_MARKER = "__AWAIT_COWORKER__"


class SendMessageToCoworkerTool(BaseTool):
    name = "send_message_to_coworker"
    description = (
        "Send a message to another employee (coworker) or the human user. "
        "Use this to collaborate with teammates, ask for their input, delegate work, "
        "or report status. Set wait_for_reply=true to pause and wait for their response, "
        "or false to continue working immediately."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to_employee_id": {
                    "type": "string",
                    "description": "The employee ID to send the message to. Use 'human' to message the user.",
                },
                "to_employee_name": {
                    "type": "string",
                    "description": "The name of the recipient (for display purposes)",
                },
                "message": {
                    "type": "string",
                    "description": "The message content to send",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation ID to thread messages in. If omitted, a new conversation is started.",
                },
                "reply_to": {
                    "type": "string",
                    "description": "The message ID this is a reply to (if replying to a specific message)",
                },
                "wait_for_reply": {
                    "type": "boolean",
                    "description": "If true, pause and wait for the recipient to reply before continuing. Default true.",
                },
            },
            "required": ["to_employee_id", "message"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        to_employee_id = parameters.get("to_employee_id", "")
        to_employee_name = parameters.get("to_employee_name", "")
        message_content = parameters.get("message", "")
        conversation_id = parameters.get("conversation_id", "")
        reply_to = parameters.get("reply_to", "")
        wait_for_reply = parameters.get("wait_for_reply", True)

        if not to_employee_id:
            return ToolResult(False, "", error="to_employee_id is required")
        if not message_content:
            return ToolResult(False, "", error="message is required")

        # Extract sender info from context (set by the ReAct loop)
        ctx = context or {}
        sender_id = ctx.get("employee_id", "unknown")
        sender_name = ctx.get("employee_name", "Unknown Employee")
        owner_id = ctx.get("owner_id", "")

        # Determine recipient type
        if to_employee_id == "human":
            recipient_type = SenderType.HUMAN
            recipient_id = ctx.get("user_id", "human")
            recipient_name = to_employee_name or "User"
        else:
            recipient_type = SenderType.EMPLOYEE
            recipient_id = to_employee_id
            recipient_name = to_employee_name or to_employee_id

        if not conversation_id:
            conversation_id = f"conv_{uuid4().hex[:12]}"

        msg_id = f"msg_{uuid4().hex[:12]}"
        msg = TeamMessage(
            id=msg_id,
            conversation_id=conversation_id,
            sender_type=SenderType.EMPLOYEE,
            sender_id=sender_id,
            sender_name=sender_name,
            content=message_content,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            status=MessageStatus.PENDING,
            reply_to=reply_to,
            owner_id=owner_id,
            created_at=datetime.now(),
        )

        store = TeamStore()
        store.send_message(msg)

        # If replying to a message, mark the original as replied
        if reply_to:
            store.mark_replied(reply_to)

        if wait_for_reply:
            # Return marker — the ReAct loop will pause and wait for coworker reply
            return ToolResult(
                success=True,
                output=AWAIT_COWORKER_MARKER,
                data={
                    "marker": AWAIT_COWORKER_MARKER,
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "to_employee_id": recipient_id,
                    "to_employee_name": recipient_name,
                    "recipient_type": recipient_type.value,
                    "message": message_content,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                },
            )
        else:
            # Fire and forget — continue immediately
            return ToolResult(
                success=True,
                output=(
                    f"Message sent to {recipient_name} (id: {recipient_id}). "
                    f"Message ID: {msg_id}, Conversation: {conversation_id}. "
                    f"Not waiting for reply — continuing."
                ),
                data={
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "to_employee_id": recipient_id,
                    "status": "sent",
                },
            )
