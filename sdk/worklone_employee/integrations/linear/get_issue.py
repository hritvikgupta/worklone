from typing import Any, Dict, List
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearGetIssueTool(BaseTool):
    name = "linear_get_issue"
    description = "Get a single issue by ID from Linear with full details"
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
                "issueId": {
                    "type": "string",
                    "description": "Linear issue ID",
                }
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
        
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            title
            description
            priority
            estimate
            url
            createdAt
            updatedAt
            completedAt
            canceledAt
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
        }
        """
        
        body = {
            "query": query,
            "variables": {
                "id": parameters["issueId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                
                data = response.json()
                
                if isinstance(data, dict) and "errors" in data and data["errors"]:
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "Failed to fetch issue") if errors else "GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                if "data" not in data or "issue" not in data["data"]:
                    return ToolResult(success=False, output="", error="No issue data in response")
                
                issue = data["data"]["issue"]
                
                transformed_issue = {
                    "id": issue.get("id"),
                    "title": issue.get("title"),
                    "description": issue.get("description"),
                    "priority": issue.get("priority"),
                    "estimate": issue.get("estimate"),
                    "url": issue.get("url"),
                    "createdAt": issue.get("createdAt"),
                    "updatedAt": issue.get("updatedAt"),
                    "completedAt": issue.get("completedAt"),
                    "canceledAt": issue.get("canceledAt"),
                    "archivedAt": issue.get("archivedAt"),
                    "state": issue.get("state"),
                    "assignee": issue.get("assignee"),
                    "teamId": issue.get("team", {}).get("id") if issue.get("team") else None,
                    "projectId": issue.get("project", {}).get("id") if issue.get("project") else None,
                    "labels": issue.get("labels", {}).get("nodes", []),
                }
                
                transformed = {"issue": transformed_issue}
                output_str = json.dumps(transformed)
                
                return ToolResult(success=True, output=output_str, data=transformed)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")