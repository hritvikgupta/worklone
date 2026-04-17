"""
CheckMessagesTool — checks unread messages from coworkers or the human.

Employees use this to see if anyone has sent them a message. This enables
pull-based communication where an employee periodically checks for new
messages alongside the push-based approach (where the ReAct loop wakes
them when a coworker sends a message with wait_for_reply=true).
"""

from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.db.stores.team_store import TeamStore


class CheckMessagesTool(BaseTool):
    name = "check_messages"
    description = (
        "Check for unread messages from coworkers or the human user. "
        "Returns all pending messages addressed to you. Use this to see if "
        "anyone needs your input or has sent you information. You can also "
        "view the full conversation history for a given conversation."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["unread", "conversation", "between"],
                    "description": (
                        "Action: 'unread' to get unread messages (default), "
                        "'conversation' to get all messages in a conversation thread, "
                        "'between' to get messages between you and a specific coworker."
                    ),
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Conversation ID to retrieve (for 'conversation' action)",
                },
                "coworker_id": {
                    "type": "string",
                    "description": "Coworker employee ID (for 'between' action)",
                },
                "mark_as_read": {
                    "type": "boolean",
                    "description": "Mark retrieved unread messages as read. Default true.",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action", "unread")
        conversation_id = parameters.get("conversation_id", "")
        coworker_id = parameters.get("coworker_id", "")
        mark_as_read = parameters.get("mark_as_read", True)

        ctx = context or {}
        employee_id = ctx.get("employee_id", "")

        if not employee_id:
            return ToolResult(False, "", error="Could not determine your employee ID from context")

        store = TeamStore()

        if action == "conversation":
            if not conversation_id:
                return ToolResult(False, "", error="conversation_id is required for 'conversation' action")
            messages = store.get_conversation(conversation_id)
            return ToolResult(
                success=True,
                output=self._format_messages(messages, f"Conversation {conversation_id}"),
                data={"messages": [self._msg_to_dict(m) for m in messages]},
            )

        elif action == "between":
            if not coworker_id:
                return ToolResult(False, "", error="coworker_id is required for 'between' action")
            messages = store.get_messages_between(employee_id, coworker_id)
            return ToolResult(
                success=True,
                output=self._format_messages(messages, f"Messages with {coworker_id}"),
                data={"messages": [self._msg_to_dict(m) for m in messages]},
            )

        else:
            # Default: unread messages
            messages = store.get_unread_messages(employee_id, "employee")
            if mark_as_read:
                for msg in messages:
                    store.mark_read(msg.id)

            if not messages:
                return ToolResult(
                    success=True,
                    output="No unread messages.",
                    data={"messages": [], "count": 0},
                )

            return ToolResult(
                success=True,
                output=self._format_messages(messages, "Unread messages"),
                data={
                    "messages": [self._msg_to_dict(m) for m in messages],
                    "count": len(messages),
                },
            )

    @staticmethod
    def _format_messages(messages, title: str) -> str:
        if not messages:
            return f"{title}: None"
        lines = [f"{title} ({len(messages)}):"]
        for msg in messages:
            direction = f"{msg.sender_name} -> {msg.recipient_name}"
            lines.append(
                f"  [{msg.id}] {direction}: {msg.content[:200]}"
                f"{'...' if len(msg.content) > 200 else ''}"
                f" (reply_to: {msg.reply_to or 'none'}, status: {msg.status.value})"
            )
        return "\n".join(lines)

    @staticmethod
    def _msg_to_dict(msg) -> dict:
        return {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_type": msg.sender_type.value,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "recipient_type": msg.recipient_type.value,
            "recipient_id": msg.recipient_id,
            "recipient_name": msg.recipient_name,
            "status": msg.status.value,
            "reply_to": msg.reply_to,
            "created_at": msg.created_at.isoformat(),
        }
