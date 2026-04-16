from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailDeleteDraftTool(BaseTool):
    name = "agentmail_delete_draft"
    description = "Delete an email draft in AgentMail"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the draft",
                },
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to delete",
                },
            },
            "required": ["inboxId", "draftId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = context.get("AGENTMAIL_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="AgentMail API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        inbox_id = parameters["inboxId"].strip()
        draft_id = parameters["draftId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts/{draft_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output="", data={"deleted": True})
                else:
                    error_msg = "Failed to delete draft"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", error_msg)
                    except Exception:
                        error_msg = response.text or error_msg
                    return ToolResult(
                        success=False, output="", error=error_msg, data={"deleted": False}
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")