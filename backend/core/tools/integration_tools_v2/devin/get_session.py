from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DevinGetSessionTool(BaseTool):
    name = "get_session"
    description = "Retrieve details of an existing Devin session including status, tags, pull requests, and structured output."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        return (context or {}).get("devin_api_key", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sessionId": {
                    "type": "string",
                    "description": "The session ID to retrieve",
                },
            },
            "required": ["sessionId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Devin API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        session_id = parameters["sessionId"]
        url = f"https://api.devin.ai/v3/organizations/sessions/{session_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")