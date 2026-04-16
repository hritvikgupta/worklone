from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZepGetUserTool(BaseTool):
    name = "zep_get_user"
    description = "Retrieve user information from Zep"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="zep_api_key",
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
                "userId": {
                    "type": "string",
                    "description": 'User ID to retrieve (e.g., "user_123")',
                }
            },
            "required": ["userId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (context or {}).get("zep_api_key")

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Zep API key not configured.")

        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
        }

        url = f"https://api.getzep.com/api/v2/users/{parameters['userId']}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")