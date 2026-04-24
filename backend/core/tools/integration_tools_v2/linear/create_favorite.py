from typing import Any, Dict
import httpx
import json
import textwrap
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateFavoriteTool(BaseTool):
    name = "linear_create_favorite"
    description = "Bookmark an issue, project, cycle, or label in Linear"
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
                "issueId": {
                    "type": "string",
                    "description": "Issue ID to favorite",
                },
                "projectId": {
                    "type": "string",
                    "description": "Project ID to favorite",
                },
                "cycleId": {
                    "type": "string",
                    "description": "Cycle ID to favorite",
                },
                "labelId": {
                    "type": "string",
                    "description": "Label ID to favorite",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        input_data: dict[str, str] = {}
        issue_id = (parameters.get("issueId") or "").strip()
        if issue_id:
            input_data["issueId"] = issue_id
        project_id = (parameters.get("projectId") or "").strip()
        if project_id:
            input_data["projectId"] = project_id
        cycle_id = (parameters.get("cycleId") or "").strip()
        if cycle_id:
            input_data["cycleId"] = cycle_id
        label_id = (parameters.get("labelId") or "").strip()
        if label_id:
            input_data["labelId"] = label_id
        
        if not input_data:
            return ToolResult(success=False, output="", error="At least one ID (issue, project, cycle, or label) must be provided")
        
        query = textwrap.dedent("""
            mutation CreateFavorite($input: FavoriteCreateInput!) {
              favoriteCreate(input: $input) {
                success
                favorite {
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
              }
            }
        """)
        
        body = {
            "query": query,
            "variables": {"input": input_data},
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Failed to create favorite") if data["errors"] else "Unknown error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("favoriteCreate")
                if not result or not result.get("success"):
                    return ToolResult(success=False, output="", error="Favorite creation was not successful")
                
                output_data = {"favorite": result["favorite"]}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=data,
                )
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")