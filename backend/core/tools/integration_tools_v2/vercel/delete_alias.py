from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelDeleteAliasTool(BaseTool):
    name = "vercel_delete_alias"
    description = "Delete an alias by its ID"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="VERCEL_ACCESS_TOKEN",
                description="Vercel Access Token",
                env_var="VERCEL_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        return (context or {}).get("VERCEL_ACCESS_TOKEN", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "aliasId": {
                    "type": "string",
                    "description": "Alias ID to delete",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["aliasId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        alias_id = (parameters.get("aliasId") or "").strip()
        if not alias_id:
            return ToolResult(success=False, output="", error="aliasId is required.")
        
        url = f"https://api.vercel.com/v2/aliases/{alias_id}"
        
        query_params: dict[str, str] = {}
        team_id = (parameters.get("teamId") or "").strip()
        if team_id:
            query_params["teamId"] = team_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")