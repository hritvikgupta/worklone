from typing import Any, Dict
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CursorLaunchAgentTool(BaseTool):
    name = "cursor_launch_agent"
    description = "Start a new cloud agent to work on a GitHub repository with the given instructions. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CURSOR_API_KEY",
                description="Cursor API key",
                env_var="CURSOR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "cursor",
            context=context,
            context_token_keys=("cursor_api_key",),
            env_token_keys=("CURSOR_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "GitHub repository URL (e.g