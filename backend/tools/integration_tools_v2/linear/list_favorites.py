from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListFavoritesTool(BaseTool):
    name = "linear_list_favorites"
    description = "List all bookmarked items for the current user in Linear"
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
            context_token_keys=("accessToken",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "first": {
                    "type": "number",
                    "description": "Number of favorites to return (default: 50)",
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
        
        url = "https://api.linear.app/graphql"
        
        variables: Dict[str, Any] = {"first": int(parameters.get("first", 50))}
        after = parameters.get("after")
        if after:
            variables["after"] = str(after).strip()
        
        query = """
        query ListFavorites($first: Int, $after: String) {
          favorites(first: $first, after: $after) {
            nodes {
              id
              type
              issue {
                id
                title
              }
              project {
                id
                name
              }
              cycle {
                id
                name
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        body = {
            "query": query,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to list favorites")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("favorites", {})
                output_dict = {
                    "favorites": result.get("nodes", []),
                    "pageInfo": {
                        "hasNextPage": result.get("pageInfo", {}).get("hasNextPage"),
                        "endCursor": result.get("pageInfo", {}).get("endCursor"),
                    },
                }
                output_str = json.dumps(output_dict)
                return ToolResult(success=True, output=output_str, data=output_dict)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")