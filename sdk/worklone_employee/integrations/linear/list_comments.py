from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListCommentsTool(BaseTool):
    name = "linear_list_comments"
    description = "List all comments on an issue in Linear"
    category = "integration"

    QUERY = """
        query ListComments($issueId: String!, $first: Int, $after: String) {
          issue(id: $issueId) {
            comments(first: $first, after: $after) {
              nodes {
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
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
    """

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
                    "description": "Linear issue ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of comments to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["issueId"],
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
        
        variables = {
            "issueId": parameters["issueId"],
        }
        first = parameters.get("first")
        variables["first"] = int(first) if first is not None else 50
        after_val = (parameters.get("after") or "").strip()
        if after_val:
            variables["after"] = after_val
        
        body = {
            "query": self.QUERY,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")