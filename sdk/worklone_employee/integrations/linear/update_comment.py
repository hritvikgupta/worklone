from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearUpdateCommentTool(BaseTool):
    name = "linear_update_comment"
    description = "Edit a comment in Linear"
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
                    "description": "Comment ID to update",
                },
                "body": {
                    "type": "string",
                    "description": "New comment text (supports Markdown)",
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

        input_dict: Dict[str, Any] = {}
        body = parameters.get("body")
        if body is not None and body != "":
            input_dict["body"] = body

        json_body = {
            "query": """
            mutation UpdateComment($id: String!, $input: CommentUpdateInput!) {
              commentUpdate(id: $id, input: $input) {
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
                }
              }
            }
            """,
            "variables": {
                "id": parameters["commentId"],
                "input": input_dict,
            },
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False, output="", error=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")

        try:
            data = response.json()
        except Exception:
            return ToolResult(success=False, output=response.text, error="Invalid JSON response")

        if data.get("errors"):
            errors = data["errors"]
            error_msg = errors[0].get("message", "Failed to update comment") if errors else "GraphQL error"
            return ToolResult(success=False, output="", error=error_msg)

        result = data.get("data", {}).get("commentUpdate", {})
        if not result.get("success"):
            return ToolResult(success=False, output="", error="Comment update was not successful")

        comment = result.get("comment", {})
        structured_output = {"comment": comment}
        return ToolResult(
            success=True, output=json.dumps(structured_output), data=structured_output
        )