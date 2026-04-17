from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListUsersTool(BaseTool):
    name = "linear_list_users"
    description = "List all users in the Linear workspace"
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
                "includeDisabled": {
                    "type": "boolean",
                    "description": "Include disabled/inactive users",
                },
                "first": {
                    "type": "number",
                    "description": "Number of users to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query = """
        query ListUsers($includeDisabled: Boolean, $first: Int, $after: String) {
          users(includeDisabled: $includeDisabled, first: $first, after: $after) {
            nodes {
              id
              name
              email
              displayName
              active
              admin
              avatarUrl
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        variables = {
            "includeDisabled": bool(parameters.get("includeDisabled", False)),
        }
        first = parameters.get("first")
        variables["first"] = int(first) if first is not None else 50
        after = parameters.get("after")
        if after:
            after_stripped = str(after).strip()
            if after_stripped:
                variables["after"] = after_stripped
        
        body = {
            "query": query,
            "variables": variables,
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except ValueError:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list users")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data["data"]["users"]
                output_data = {
                    "users": result["nodes"],
                    "pageInfo": {
                        "hasNextPage": result["pageInfo"]["hasNextPage"],
                        "endCursor": result["pageInfo"]["endCursor"],
                    },
                }
                output_str = json.dumps(output_data, indent=2)
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")