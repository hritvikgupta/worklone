from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZepAddMessagesTool(BaseTool):
    name = "zep_add_messages"
    description = "Add messages to an existing thread"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZEP_API_KEY",
                description="Your Zep API key",
                env_var="ZEP_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": 'Thread ID to add messages to (e.g., "thread_abc123")',
                },
                "messages": {
                    "type": "string",
                    "description": 'Array of message objects with role and content (e.g., "[{\"role\": \"user\", \"content\": \"Hello\"}]")',
                },
            },
            "required": ["threadId", "messages"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ZEP_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Zep API key not configured.")

        thread_id = parameters.get("threadId")
        if not thread_id:
            return ToolResult(success=False, output="", error="threadId is required.")

        messages_input = parameters.get("messages")
        if not messages_input:
            return ToolResult(success=False, output="", error="messages is required.")

        try:
            if isinstance(messages_input, str):
                messages_array = json.loads(messages_input)
            else:
                messages_array = messages_input
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Messages must be a valid JSON array")

        if not isinstance(messages_array, list) or len(messages_array) == 0:
            return ToolResult(success=False, output="", error="Messages must be a non-empty array")

        for msg in messages_array:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                return ToolResult(success=False, output="", error="Each message must have role and content properties")

        url = f"https://api.getzep.com/api/v2/threads/{thread_id}/messages"

        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "messages": messages_array,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    text = response.text
                    if text and text.strip():
                        try:
                            data = response.json()
                            message_ids = data.get("message_uuids", [])
                        except:
                            return ToolResult(success=False, output="", error="Invalid response format from Zep API")
                    else:
                        message_ids = []

                    output_data = {
                        "threadId": thread_id,
                        "added": True,
                        "messageIds": message_ids,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    error_text = response.text or "Unknown error"
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Zep API error ({response.status_code}): {error_text}",
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")