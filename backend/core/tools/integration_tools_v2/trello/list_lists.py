from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloListListsTool(BaseTool):
    name = "trello_list_lists"
    description = "List all lists on a Trello board"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="TRELLO_API_KEY",
                description="Trello API Key",
                env_var="TRELLO_API_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="TRELLO_ACCESS_TOKEN",
                description="Trello OAuth access token",
                env_var="TRELLO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "trello",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("TRELLO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Trello board ID (24-character hex string)",
                },
            },
            "required": ["boardId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        api_key = os.environ.get("TRELLO_API_KEY")
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Trello API key not configured.")
        
        board_id = parameters.get("boardId")
        if not board_id:
            return ToolResult(success=False, output="", error="Board ID is required")
        
        url = f"https://api.trello.com/1/boards/{board_id}/lists?key={api_key}&token={access_token}"
        
        headers = {
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if isinstance(data, list):
                    result = {
                        "lists": data,
                        "count": len(data),
                    }
                    return ToolResult(success=True, output=response.text, data=result)
                else:
                    error_msg = data.get("message") or data.get("error") or "Invalid response from Trello API"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")