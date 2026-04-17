from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentMailGetDraftTool(BaseTool):
    name = "agentmail_get_draft"
    description = "Get details of a specific email draft in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "AgentMail API key",
                },
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox the draft belongs to",
                },
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to retrieve",
                },
            },
            "required": ["apiKey", "inboxId", "draftId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters["apiKey"]
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        inbox_id = parameters["inboxId"].strip()
        draft_id = parameters["draftId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts/{draft_id}"

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")