from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LoopsListMailingListsTool(BaseTool):
    name = "loops_list_mailing_lists"
    description = "Retrieve all mailing lists from your Loops account. Returns each list with its ID, name, description, and public/private status."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
        
        url = "https://app.loops.so/api/v1/lists"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not isinstance(data, list):
                        error_msg = data.get("message") if isinstance(data, dict) else "Failed to list mailing lists"
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    mailing_lists = []
                    for list_item in data:
                        mailing_lists.append({
                            "id": list_item.get("id", "") or "",
                            "name": list_item.get("name", "") or "",
                            "description": list_item.get("description"),
                            "isPublic": list_item.get("isPublic", False),
                        })
                    
                    output_data = {"mailingLists": mailing_lists}
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")