from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListWorkflowStatesTool(BaseTool):
    name = "linear_list_workflow_states"
    description = "List all workflow states (statuses) in Linear"
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
                "teamId": {
                    "type": "string",
                    "description": "Filter by team ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of states to return (default: 50)",
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
        
        variables: Dict[str, Any] = {}
        first_val = parameters.get("first")
        variables["first"] = int(first_val) if first_val is not None else 50
        
        team_id = parameters.get("teamId")
        if team_id:
            variables["filter"] = {"team": {"id": {"eq": team_id}}}
        
        after_val = parameters.get("after")
        if after_val:
            variables["after"] = str(after_val).strip()
        
        body = {
            "query": """
                query ListWorkflowStates($filter: WorkflowStateFilter, $first: Int, $after: String) {
                  workflowStates(filter: $filter, first: $first, after: $after) {
                    nodes {
                      id
                      name
                      description
                      type
                      color
                      position
                      createdAt
                      updatedAt
                      archivedAt
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
            """,
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
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to list workflow states")
                    return ToolResult(success=False, output="", error=error_msg)
                
                if "data" not in data or "workflowStates" not in data["data"]:
                    return ToolResult(success=False, output="", error="Unexpected response structure")
                
                result = data["data"]["workflowStates"]
                output_data = {
                    "states": result["nodes"],
                    "pageInfo": {
                        "hasNextPage": result["pageInfo"]["hasNextPage"],
                        "endCursor": result["pageInfo"]["endCursor"],
                    },
                }
                return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")