from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListCyclesTool(BaseTool):
    name = "linear_list_cycles"
    description = "List cycles (sprints/iterations) in Linear"
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
                "teamId": {
                    "type": "string",
                    "description": "Filter by team ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of cycles to return (default: 50)",
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
        
        query = """
        query ListCycles($filter: CycleFilter, $first: Int, $after: String) {
          cycles(filter: $filter, first: $first, after: $after) {
            nodes {
              id
              number
              name
              startsAt
              endsAt
              completedAt
              progress
              createdAt
              team {
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
        
        filter_ = {}
        team_id = parameters.get("teamId")
        if team_id:
            filter_["team"] = {"id": {"eq": team_id}}
        
        variables: dict[str, Any] = {
            "first": int(parameters.get("first", 50)),
        }
        if filter_:
            variables["filter"] = filter_
        after_val = parameters.get("after")
        if after_val:
            stripped_after = str(after_val).strip()
            if stripped_after:
                variables["after"] = stripped_after
        
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
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list cycles") if data["errors"] else "Failed to list cycles"
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")