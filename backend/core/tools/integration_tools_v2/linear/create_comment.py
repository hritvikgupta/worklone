from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateCommentTool(BaseTool):
    name = "linear_create_comment"
    description = "Add a comment to an issue in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token for Linear",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "issueId": {
                    "type": "string",
                    "description": "Linear issue ID to comment on",
                },
                "body": {
                    "type": "string",
                    "description": "Comment text (supports Markdown)",
                },
            },
            "required": ["issueId", "body"],
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

        json_body = {
            "query": """
                mutation CreateComment($input: CommentCreateInput!) {
                  commentCreate(input: $input) {
                    success
                    comment {
                      id
                      body
                      createdAt
                      updatedAt
                      user {
                        id
                        name
                        email
                      }
                      issue {
                        id
                        title
                      }
                    }
                  }
                }
            """,
            "variables": {
                "input": {
                    "issueId": parameters["issueId"],
                    "body": parameters["body"],
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if not (200 <= response.status_code < 300):
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )

                data = response.json()

                if data.get("errors"):
                    errors = data["errors"]
                    if errors:
                        error_msg = (
                            errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
                        )
                        return ToolResult(success=False, output="", error=error_msg or "Failed to create comment")

                if "data" not in data or "commentCreate" not in data["data"]:
                    return ToolResult(
                        success=False, output="", error="Unexpected response structure"
                    )

                result = data["data"]["commentCreate"]
                if not result.get("success", False):
                    return ToolResult(
                        success=False, output="", error="Comment creation was not successful"
                    )

                comment_data = {"comment": result["comment"]}
                output_str = json.dumps(comment_data)

                return ToolResult(success=True, output=output_str, data=comment_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")