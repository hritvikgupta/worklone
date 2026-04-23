from typing import Any, Dict
import httpx
import os
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloCreateCardTool(BaseTool):
    name = "trello_create_card"
    description = "Create a new card on a Trello board"
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
            context_token_keys=("accessToken",),
            env_token_keys=("TRELLO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("TRELLO_API_KEY")
        if not api_key:
            api_key = os.getenv("TRELLO_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key or ""

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
                    "description": "Trello list ID (24-character hex string)",
                },
                "name": {
                    "type": "string",
                    "description": "Name/title of the card",
                },
                "desc": {
                    "type": "string",
                    "description": "Description of the card",
                },
                "pos": {
                    "type": "string",
                    "description": "Position of the card (top, bottom, or positive float)",
                },
                "due": {
                    "type": "string",
                    "description": "Due date (ISO 8601 format)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label IDs (24-character hex strings)",
                },
            },
            "required": ["boardId", "listId", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Trello API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        url = f"https://api.trello.com/1/cards?key={api_key}&token={access_token}"
        
        body = {
            "idList": parameters["listId"],
            "name": parameters["name"],
        }
        if "desc" in parameters:
            body["desc"] = parameters["desc"]
        if "pos" in parameters:
            body["pos"] = parameters["pos"]
        if "due" in parameters:
            body["due"] = parameters["due"]
        if "labels" in parameters:
            body["idLabels"] = parameters["labels"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if data.get("id"):
                            card_data = {"card": data}
                            return ToolResult(success=True, output=json.dumps(card_data), data=card_data)
                        else:
                            return ToolResult(
                                success=False,
                                output="",
                                error=data.get("message", "Failed to create card")
                            )
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")