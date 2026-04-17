from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HexListUsersTool(BaseTool):
    name = "hex_list_users"
    description = "List all users in the Hex workspace with optional filtering and sorting."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HEX_API_KEY",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hex",
            context=context,
            context_token_keys=("hex_api_key",),
            env_token_keys=("HEX_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of users to return (1-100, default: 25)",
                },
                "sortBy": {
                    "type": "string",
                    "description": "Sort by field: NAME or EMAIL",
                },
                "sortDirection": {
                    "type": "string",
                    "description": "Sort direction: ASC or DESC",
                },
                "groupId": {
                    "type": "string",
                    "description": "Filter users by group UUID",
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
        
        url = "https://app.hex.tech/api/v1/users"
        query_params = {
            "limit": parameters.get("limit"),
            "sortBy": parameters.get("sortBy"),
            "sortDirection": parameters.get("sortDirection"),
            "groupId": parameters.get("groupId"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    users = data if isinstance(data, list) else data.get("values", [])
                    transformed_users = [
                        {
                            "id": u.get("id"),
                            "name": u.get("name"),
                            "email": u.get("email"),
                            "role": u.get("role"),
                        }
                        for u in users
                    ]
                    output_data = {
                        "users": transformed_users,
                        "total": len(transformed_users),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")