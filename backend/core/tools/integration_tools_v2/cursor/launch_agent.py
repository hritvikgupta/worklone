from typing import Any
import base64
import httpx

from backend.lib.oauth.oauth_common import resolve_oauth_connection
from backend.core.tools.system_tools.base import BaseTool, CredentialRequirement, ToolResult


class CursorLaunchAgentTool(BaseTool):
    name = "cursor_launch_agent"
    description = "Start a new cloud agent to work on a repository with instructions."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return (
            not normalized
            or normalized.startswith("your-")
            or "replace-me" in normalized
            or normalized == "ya29...."
        )

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
            context_token_keys=("cursor_api_key", "provider_token"),
            env_token_keys=("CURSOR_API_KEY", "CURSOR_ACCESS_TOKEN"),
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
                    "description": "Repository URL or slug (for example https://github.com/org/repo).",
                },
                "prompt": {
                    "type": "string",
                    "description": "Instructions for the launched agent.",
                },
                "branch": {
                    "type": "string",
                    "description": "Optional branch name to target.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the launched task.",
                },
                "prUrl": {
                    "type": "string",
                    "description": "Optional pull request URL to attach the agent to.",
                },
            },
            "required": ["repository", "prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Cursor API key not configured.")

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "repository": parameters["repository"],
            "prompt": parameters["prompt"],
        }
        if parameters.get("branch"):
            payload["branch"] = parameters["branch"]
        if parameters.get("title"):
            payload["title"] = parameters["title"]
        if parameters.get("prUrl"):
            payload["prUrl"] = parameters["prUrl"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.cursor.com/v0/agents",
                    headers=headers,
                    json=payload,
                )

            if response.status_code not in {200, 201, 202}:
                return ToolResult(success=False, output="", error=response.text)

            data = response.json()
            agent_id = data.get("id") or data.get("agentId") or data.get("data", {}).get("id")
            output = agent_id or response.text
            return ToolResult(success=True, output=output, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
