from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListUsersTool(BaseTool):
    name = "gong_list_users"
    description = "List all users in your Gong account."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKey",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="accessKeySecret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
                "includeAvatars": {
                    "type": "string",
                    "description": "Whether to include avatar URLs (true/false)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("accessKey") if context else None
        access_key_secret = context.get("accessKeySecret") if context else None
        
        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access keys not configured.")
        
        credentials = f"{access_key}:{access_key_secret}"
        auth_header = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.gong.io/v2/users"
        params = {}
        cursor = parameters.get("cursor")
        if cursor:
            params["cursor"] = cursor
        include_avatars = parameters.get("includeAvatars")
        if include_avatars:
            params["includeAvatars"] = include_avatars
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")