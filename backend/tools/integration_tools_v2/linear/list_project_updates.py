from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListProjectUpdatesTool(BaseTool):
    name = "linear_list_project_updates"
    description = "List all status updates for a project in Linear"
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
                "projectId": {
                    "type": "string",
                    "description": "Project ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of updates to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["projectId"],
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
        
        query = """
        query ListProjectUpdates($projectId: String!, $first: Int, $after: String) {
          project(id: $projectId) {
            projectUpdates(first: $first, after: $after) {
              nodes {
                id
                body
                health
                createdAt
                user {
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
        }
        """
        
        variables: Dict[str, Any] = {
            "projectId": parameters["projectId"],
            "first": int(parameters.get("first", 50)),
        }
        after = parameters.get("after")
        if after:
            variables["after"] = str(after).strip()
        
        json_body = {
            "query": query,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "GraphQL error") if isinstance(errors, list) and errors else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)
                
                if not data.get("data", {}).get("project"):
                    return ToolResult(success=False, output="", error="Project not found")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")