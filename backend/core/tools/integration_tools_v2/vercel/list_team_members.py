from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListTeamMembersTool(BaseTool):
    name = "vercel_list_team_members"
    description = "List all members of a Vercel team"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Vercel Access Token",
                env_var="VERCEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("apiKey") if context else None
        if self._is_placeholder_token(token):
            token = os.getenv("VERCEL_API_KEY")
        if self._is_placeholder_token(token):
            raise ValueError("Access token not configured.")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": "The team ID to list members for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of members to return",
                },
                "role": {
                    "type": "string",
                    "description": "Filter by role (OWNER, MEMBER, DEVELOPER, SECURITY, BILLING, VIEWER, VIEWER_FOR_PLUS, CONTRIBUTOR)",
                },
                "since": {
                    "type": "number",
                    "description": "Timestamp in milliseconds to only include members added since then",
                },
                "until": {
                    "type": "number",
                    "description": "Timestamp in milliseconds to only include members added until then",
                },
                "search": {
                    "type": "string",
                    "description": "Search team members by their name, username, and email",
                },
            },
            "required": ["teamId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        team_id = parameters["teamId"].strip()
        query_params: Dict[str, str] = {}
        if "limit" in parameters and parameters["limit"] is not None:
            query_params["limit"] = str(parameters["limit"])
        if "role" in parameters and parameters["role"]:
            query_params["role"] = str(parameters["role"]).strip()
        if "since" in parameters and parameters["since"] is not None:
            query_params["since"] = str(parameters["since"])
        if "until" in parameters and parameters["until"] is not None:
            query_params["until"] = str(parameters["until"])
        if "search" in parameters and parameters["search"]:
            query_params["search"] = str(parameters["search"]).strip()
        
        url = f"https://api.vercel.com/v3/teams/{team_id}/members"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")