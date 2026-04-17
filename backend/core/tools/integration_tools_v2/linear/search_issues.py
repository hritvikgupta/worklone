from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearSearchIssuesTool(BaseTool):
    name = "linear_search_issues"
    description = "Search for issues in Linear using full-text search"
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
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "teamId": {
                    "type": "string",
                    "description": "Filter by team ID",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived issues in search results",
                },
                "first": {
                    "type": "number",
                    "description": "Number of results to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["query"],
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
        
        filter_dict: Dict[str, Any] = {}
        team_id = parameters.get("teamId")
        if team_id:
            filter_dict = {"team": {"id": {"eq": team_id}}}
        
        variables: Dict[str, Any] = {
            "term": parameters["query"],
            "first": int(parameters.get("first", 50)),
            "includeArchived": bool(parameters.get("includeArchived", False)),
        }
        after = (parameters.get("after") or "").strip()
        if after:
            variables["after"] = after
        if filter_dict:
            variables["filter"] = filter_dict
        
        query = """
        query SearchIssues($term: String!, $filter: IssueFilter, $first: Int, $after: String, $includeArchived: Boolean) {
          searchIssues(term: $term, filter: $filter, first: $first, after: $after, includeArchived: $includeArchived) {
            nodes {
              id
              title
              description
              priority
              estimate
              url
              createdAt
              updatedAt
              archivedAt
              state {
                id
                name
                type
              }
              assignee {
                id
                name
                email
              }
              team {
                id
                name
              }
              project {
                id
                name
              }
              labels {
                nodes {
                  id
                  name
                  color
                }
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
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "Failed to search issues") if isinstance(errors, list) and errors else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")