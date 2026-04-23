from typing import Any, Dict
import httpx
import os
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloListCardsTool(BaseTool):
    name = "trello_list_cards"
    description = "List all cards on a Trello board"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="TRELLO_API_KEY",
                description="Trello API Key (generate at https://trello.com/app-key)",
                env_var="TRELLO_API_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="TRELLO_ACCESS_TOKEN",
                description="Trello access token",
                env_var="TRELLO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context and "trello_api_key" in context:
            api_key = context["trello_api_key"]
        if api_key is None:
            api_key = os.environ.get("TRELLO_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            raise ValueError("Trello API key not configured.")
        return api_key

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
                "listId": {
                    "type": "string",
                    "description": "Trello list ID to filter cards (24-character hex string)",
                },
            },
            "required": ["boardId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            api_key = await self._resolve_api_key(context)
            access_token = await self._resolve_access_token(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Trello credentials not configured.")

        board_id = parameters["boardId"]
        list_id = parameters.get("listId")
        url = f"https://api.trello.com/1/boards/{board_id}/cards"

        query_params: Dict[str, str] = {
            "key": api_key,
            "token": access_token,
            "fields": "id,name,desc,url,idBoard,idList,closed,labels,due,dueComplete",
        }
        if list_id:
            query_params["list"] = list_id

        headers = {
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        return ToolResult(success=False, output="", error="Invalid JSON response from Trello API")

                    if not isinstance(data, list):
                        return ToolResult(
                            success=False,
                            output="",
                            error="Invalid response from Trello API",
                        )

                    transformed = {
                        "cards": data,
                        "count": len(data),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed),
                        data=transformed,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")