from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearDeleteCommentTool(BaseTool):
    name = "linear_delete_comment"
    description = "Delete a comment from Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "commentId": {
                    "type": "string",
                    "description": "Comment ID to delete",
                },
            },
            "required": ["commentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.linear.app/graphql"

        body = {
            "query": """
                mutation DeleteComment($id: String!) {
                  commentDelete(id: $id) {
                    success
                  }
                }
            """,
            "variables": {
                "id": parameters["commentId"],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")

                if data.get("errors"):
                    error_msg = (
                        data["errors"][0].get("message", "Failed to delete comment")
                        if isinstance(data["errors"], list) and data["errors"]
                        else "GraphQL errors"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                if "data" not in data or "commentDelete" not in data["data"]:
                    return ToolResult(
                        success=False, output="", error="Unexpected response structure"
                    )

                success = data["data"]["commentDelete"]["success"]

                return ToolResult(success=success, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")