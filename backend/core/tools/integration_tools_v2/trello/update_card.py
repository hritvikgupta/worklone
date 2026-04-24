import os
import httpx
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloUpdateCardTool(BaseTool):
    name = "trello_update_card"
    description = "Update an existing card on Trello"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("TRELLO_API_KEY")
        if not api_key:
            api_key = os.getenv("TRELLO_API_KEY")
        return api_key or ""

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "trello",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("TRELLO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cardId": {
                    "type": "string",
                    "description": "Trello card ID (24-character hex string)",
                },
                "name": {
                    "type": "string",
                    "description": "New name/title of the card",
                },
                "desc": {
                    "type": "string",
                    "description": "New description of the card",
                },
                "closed": {
                    "type": "boolean",
                    "description": "Archive/close the card (true) or reopen it (false)",
                },
                "idList": {
                    "type": "string",
                    "description": "Trello list ID to move card to (24-character hex string)",
                },
                "due": {
                    "type": "string",
                    "description": "Due date (ISO 8601 format)",
                },
                "dueComplete": {
                    "type": "boolean",
                    "description": "Mark the due date as complete",
                },
            },
            "required": ["cardId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        api_key = self._resolve_api_key(context)
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Trello API key not configured.")

        card_id = parameters.get("cardId")
        if not card_id:
            return ToolResult(success=False, output="", error="Card ID is required")

        body: Dict[str, Any] = {}
        if "name" in parameters:
            body["name"] = parameters["name"]
        if "desc" in parameters:
            body["desc"] = parameters["desc"]
        if "closed" in parameters:
            body["closed"] = parameters["closed"]
        if "idList" in parameters:
            body["idList"] = parameters["idList"]
        if "due" in parameters:
            body["due"] = parameters["due"]
        if "dueComplete" in parameters:
            body["dueComplete"] = parameters["dueComplete"]

        if len(body) == 0:
            return ToolResult(success=False, output="", error="At least one field must be provided to update")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"https://api.trello.com/1/cards/{card_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    url,
                    headers=headers,
                    params={"key": api_key, "token": access_token},
                    json=body,
                )

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")