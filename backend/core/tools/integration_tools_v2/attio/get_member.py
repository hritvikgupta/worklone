from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioGetMemberTool(BaseTool):
    name = "attio_get_member"
    description = "Get a single workspace member by ID"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="The OAuth access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "memberId": {
                    "type": "string",
                    "description": "The workspace member ID",
                },
            },
            "required": ["memberId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        member_id = parameters["memberId"].strip()
        url = f"https://api.attio.com/v2/workspace_members/{member_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    m = data.get("data", {})
                    output_dict = {
                        "memberId": m.get("id", {}).get("workspace_member_id") if m.get("id") else None,
                        "firstName": m.get("first_name"),
                        "lastName": m.get("last_name"),
                        "avatarUrl": m.get("avatar_url"),
                        "emailAddress": m.get("email_address"),
                        "accessLevel": m.get("access_level"),
                        "createdAt": m.get("created_at"),
                    }
                    return ToolResult(success=True, output=str(output_dict), data=output_dict)
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("message") or response.text or "Failed to get workspace member"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")