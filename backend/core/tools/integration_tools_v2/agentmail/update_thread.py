from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailUpdateThreadTool(BaseTool):
    name = "agentmail_update_thread"
    description = "Add or remove labels on an email thread in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AGENTMAIL_API_KEY",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        if context is None:
            return ""
        return context.get("AGENTMAIL_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the thread",
                },
                "threadId": {
                    "type": "string",
                    "description": "ID of the thread to update",
                },
                "addLabels": {
                    "type": "string",
                    "description": "Comma-separated labels to add to the thread",
                },
                "removeLabels": {
                    "type": "string",
                    "description": "Comma-separated labels to remove from the thread",
                },
            },
            "required": ["inboxId", "threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        inbox_id = parameters["inboxId"].strip()
        thread_id = parameters["threadId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/threads/{thread_id}"

        body: dict[str, list[str]] = {}
        add_labels = parameters.get("addLabels")
        if add_labels:
            body["add_labels"] = [l.strip() for l in add_labels.split(",")]
        remove_labels = parameters.get("removeLabels")
        if remove_labels:
            body["remove_labels"] = [l.strip() for l in remove_labels.split(",")]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if 200 <= response.status_code < 300:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")