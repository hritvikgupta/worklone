from typing import Any, Dict
import httpx
import os
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloGetActionsTool(BaseTool):
    name = "trello_get_actions"
    description = "Get activity/actions from a board or card"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="TRELLO_ACCESS_TOKEN",
                description="Trello access token",
                env_var="TRELLO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "trello",
            context=context,
            context_token_keys=("trello_token",),
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
                    "description": "Trello board ID (24-character hex string). Either boardId or cardId required",
                },
                "cardId": {
                    "type": "string",
                    "description": "Trello card ID (24-character hex string). Either boardId or cardId required",
                },
                "filter": {
                    "type": "string",
                    "description": 'Filter actions by type (e.g., "commentCard,updateCard,createCard" or "all")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of actions to return (default: 50, max: 1000)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        api_key = os.getenv("TRELLO_API_KEY")
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Trello API key not configured.")

        board_id = parameters.get("boardId")
        card_id = parameters.get("cardId")
        if not board_id and not card_id:
            return ToolResult(success=False, output="", error="Either boardId or cardId is required")
        if board_id and card_id:
            return ToolResult(success=False, output="", error="Provide either boardId or cardId, not both")

        id_ = board_id or card_id
        type_ = "boards" if board_id else "cards"
        filter_ = parameters.get("filter")
        limit = int(parameters.get("limit") or 50)

        query_params = {
            "key": api_key,
            "token": access_token,
            "fields": "id,type,date,memberCreator,data",
            "limit": limit,
        }
        if filter_:
            query_params["filter"] = filter_

        url = f"https://api.trello.com/1/{type_}/{id_}/actions?{urlencode(query_params)}"

        headers = {
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                return ToolResult(success=False, output="", error=response.text)

            try:
                data = response.json()
            except Exception:
                return ToolResult(success=False, output="", error="Invalid JSON from Trello API")

            if not isinstance(data, list):
                return ToolResult(success=False, output="", error="Invalid response from Trello API")

            result = {
                "actions": data,
                "count": len(data),
            }
            return ToolResult(success=True, output=response.text, data=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")