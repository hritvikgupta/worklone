from typing import Any, Dict
import httpx
import json
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LoopsListContactPropertiesTool(BaseTool):
    name = "loops_list_contact_properties"
    description = "Retrieve a list of contact properties from your Loops account. Returns each property with its key, label, and data type. Can filter to show all properties or only custom ones."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LOOPS_API_KEY",
                description="Loops API key for authentication",
                env_var="LOOPS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "loops",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("LOOPS_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "list": {
                    "type": "string",
                    "description": 'Filter type: "all" for all properties (default) or "custom" for custom properties only',
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
        }
        
        url = "https://app.loops.so/api/v1/contacts/properties"
        list_param = parameters.get("list")
        if list_param:
            url += f"?list={quote(list_param)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                    
                    if not isinstance(data, list):
                        error_msg = data.get("message", "Failed to list contact properties") if isinstance(data, dict) else "Failed to list contact properties"
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    properties = [
                        {
                            "key": prop.get("key", ""),
                            "label": prop.get("label", ""),
                            "type": prop.get("type", ""),
                        }
                        for prop in data
                    ]
                    output_data = {"properties": properties}
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")