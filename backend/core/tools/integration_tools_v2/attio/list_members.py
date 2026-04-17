from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListMembersTool(BaseTool):
    name = "attio_list_members"
    description = "List all workspace members in Attio"
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
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = "https://api.attio.com/v2/workspace_members"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    members = []
                    for m in data.get("data", []):
                        member = {
                            "memberId": m.get("id", {}).get("workspace_member_id"),
                            "firstName": m.get("first_name"),
                            "lastName": m.get("last_name"),
                            "avatarUrl": m.get("avatar_url"),
                            "emailAddress": m.get("email_address"),
                            "accessLevel": m.get("access_level"),
                            "createdAt": m.get("created_at"),
                        }
                        members.append(member)
                    transformed = {
                        "members": members,
                        "count": len(members),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message") or "Failed to list workspace members"
                    except Exception:
                        error_msg = response.text or "Failed to list workspace members"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")