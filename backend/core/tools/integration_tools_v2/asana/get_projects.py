from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AsanaGetProjectsTool(BaseTool):
    name = "asana_get_projects"
    description = "Retrieve all projects from an Asana workspace"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASANA_ACCESS_TOKEN",
                description="Access token",
                env_var="ASANA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "asana",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("ASANA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": "Asana workspace GID (numeric string) to retrieve projects from",
                },
            },
            "required": ["workspace"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        workspace = parameters.get("workspace")
        if not workspace:
            return ToolResult(success=False, output="", error="Workspace is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        url = f"https://app.asana.com/api/1.0/projects?workspace={workspace}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    projects = result.get("data", [])
                    mapped_projects = [
                        {
                            "gid": project.get("gid"),
                            "name": project.get("name"),
                            "resource_type": project.get("resource_type"),
                        }
                        for project in projects
                    ]
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {
                        "success": True,
                        "ts": ts,
                        "projects": mapped_projects,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    error_text = response.text
                    error_message = f"Asana API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        asana_error = errors[0] if errors else {}
                        if asana_error.get("message"):
                            error_message = asana_error["message"]
                            if asana_error.get("help"):
                                error_message += f" ({asana_error['help']})"
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False, output="", error=error_message
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")