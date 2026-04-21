from typing import Any, Dict
import httpx
import textwrap
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListProjectLabelsTool(BaseTool):
    name = "linear_list_project_labels"
    description = "List all project labels in Linear"
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
            context_token_keys=("provider_token", "access_token", "linear_token"),
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
                    "description": "Optional project ID to filter labels for a specific project",
                },
                "first": {
                    "type": "number",
                    "description": "Number of labels to return (default: 50)",
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
        
        project_id = (parameters.get("projectId") or "").strip()
        first = int(parameters.get("first", 50))
        after = (parameters.get("after") or "").strip()
        
        if project_id:
            query = textwrap.dedent("""
                query ProjectWithLabels($id: String!, $first: Int, $after: String) {
                  project(id: $id) {
                    id
                    name
                    labels(first: $first, after: $after) {
                      nodes {
                        id
                        name
                        description
                        color
                        isGroup
                        createdAt
                        updatedAt
                        archivedAt
                      }
                      pageInfo {
                        hasNextPage
                        endCursor
                      }
                    }
                  }
                }
            """)
            variables = {
                "id": project_id,
                "first": first,
            }
            if after:
                variables["after"] = after
        else:
            query = textwrap.dedent("""
                query ProjectLabels($first: Int, $after: String) {
                  projectLabels(first: $first, after: $after) {
                    nodes {
                      id
                      name
                      description
                      color
                      isGroup
                      createdAt
                      updatedAt
                      archivedAt
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                  }
                }
            """)
            variables = {
                "first": first,
            }
            if after:
                variables["after"] = after
        
        url = "https://api.linear.app/graphql"
        body = {
            "query": query,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if isinstance(data, dict) and "errors" in data and data["errors"]:
                        error_msg = data["errors"][0].get("message", "Failed to list project labels")
                        return ToolResult(success=False, output="", error=error_msg)
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")