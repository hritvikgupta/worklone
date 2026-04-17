from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateProjectMilestoneTool(BaseTool):
    name = "linear_update_project_milestone"
    description = "Update a project milestone in Linear"
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
                "milestoneId": {
                    "type": "string",
                    "description": "Project milestone ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated milestone name",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "targetDate": {
                    "type": "string",
                    "description": "Updated target date (ISO 8601)",
                },
            },
            "required": ["milestoneId"],
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
        
        input_dict: Dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_dict["name"] = name
        description = parameters.get("description")
        if description is not None and description != "":
            input_dict["description"] = description
        target_date = parameters.get("targetDate")
        if target_date is not None and target_date != "":
            input_dict["targetDate"] = target_date
        
        query = """
          mutation ProjectMilestoneUpdate($id: String!, $input: ProjectMilestoneUpdateInput!) {
            projectMilestoneUpdate(id: $id, input: $input) {
              success
              projectMilestone {
                id
                name
                description
                targetDate
                progress
                sortOrder
                status
                createdAt
                archivedAt
                project {
                  id
                }
              }
            }
          }
        """
        body = {
            "query": query,
            "variables": {
                "id": parameters["milestoneId"],
                "input": input_dict,
            },
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