from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleMeetCreateSpaceTool(BaseTool):
    name = "google_meet_create_space"
    description = "Create a new Google Meet meeting space"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_MEET_ACCESS_TOKEN",
                description="Access token for Google Meet API",
                env_var="GOOGLE_MEET_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-meet",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_MEET_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accessType": {
                    "type": "string",
                    "description": "Who can join the meeting without knocking: OPEN (anyone with link), TRUSTED (org members), RESTRICTED (only invited)",
                },
                "entryPointAccess": {
                    "type": "string",
                    "description": "Entry points allowed: ALL (all entry points) or CREATOR_APP_ONLY (only via app)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://meet.googleapis.com/v2/spaces"
        
        body: Dict[str, Any] = {}
        if parameters.get("accessType") or parameters.get("entryPointAccess"):
            config: Dict[str, str] = {}
            if access_type := parameters.get("accessType"):
                config["accessType"] = access_type
            if entry_point_access := parameters.get("entryPointAccess"):
                config["entryPointAccess"] = entry_point_access
            body["config"] = config
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")