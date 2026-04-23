from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class TrelloAddCommentTool(BaseTool):
    name = "trello_add_comment"
    description = "Add a comment to a Trello card"
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
            context_token_keys=("provider_token", "accessToken"),
            env_token_keys=("TRELLO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _resolve_api_key(self, context: dict | None) -> str:
        value = (context or {}).get("trello_api_key") or os.getenv("TRELLO_API_KEY", "")
        if self._is_placeholder_token(value):
            raise ValueError("Trello API key not configured.")
        return value

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cardId": {
                    "type": "string",
                    "description": "Trello card ID (24-character hex string)",
                },
                "text": {
                    "type": "string",
                    "description": "Comment text",
                },
            },
            "required": ["cardId", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        card_id = parameters.get("cardId")
        text = parameters.get("text")
        if not card_id or not text:
            return ToolResult(success=False, output="", error="cardId and text are required.")

        access_token = await self._resolve_access_token(context)
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Trello credentials not configured.")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"https://api.trello.com/1/cards/{card_id}/actions/comments?key={api_key}&token={access_token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={"text": text})

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")