from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveCreateProjectTool(BaseTool):
    name = "pipedrive_create_project"
    description = "Create a new project in Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the project (e.g., \"Q2 Marketing Campaign\")",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the project",
                },
                "start_date": {
                    "type": "string",
                    "description": "Project start date in YYYY-MM-DD format (e.g., \"2025-04-01\")",
                },
                "end_date": {
                    "type": "string",
                    "description": "Project end date in YYYY-MM-DD format (e.g., \"2025-06-30\")",
                },
            },
            "required": ["title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        body = {
            "title": parameters["title"],
        }
        description = parameters.get("description")
        if description:
            body["description"] = description
        start_date = parameters.get("start_date")
        if start_date:
            body["start_date"] = start_date
        end_date = parameters.get("end_date")
        if end_date:
            body["end_date"] = end_date
        
        url = "https://api.pipedrive.com/v1/projects"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if not data.get("success", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("error") or "Failed to create project in Pipedrive",
                    )
                    
                return ToolResult(
                    success=True,
                    output=response.text,
                    data={"project": data.get("data"), "success": True},
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")