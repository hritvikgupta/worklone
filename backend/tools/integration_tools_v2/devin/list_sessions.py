from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DevinListSessionsTool(BaseTool):
    name = "list_sessions"
    description = "List Devin sessions in the organization. Returns up to 100 sessions by default."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="devin_api_key",
                description="Devin API key (service user credential starting with cog_)",
                env_var="DEVIN_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of sessions to return (1-200, default: 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("devin_api_key") if context else None
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Devin API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        base_url = "https://api.devin.ai/v3/organizations/sessions"
        url = base_url
        limit = parameters.get("limit")
        if limit is not None:
            url += f"?first={int(limit)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    sessions = [
                        {
                            "sessionId": item.get("session_id"),
                            "url": item.get("url"),
                            "status": item.get("status"),
                            "statusDetail": item.get("status_detail"),
                            "title": item.get("title"),
                            "createdAt": item.get("created_at"),
                            "updatedAt": item.get("updated_at"),
                            "tags": item.get("tags"),
                        }
                        for item in items
                    ]
                    transformed_data = {"sessions": sessions}
                    return ToolResult(success=True, output=response.text, data=transformed_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")