from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AsanaCreateTaskTool(BaseTool):
    name = "asana_create_task"
    description = "Create a new task in Asana"
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
            context_token_keys=("provider_token",},
            env_token_keys=("ASANA_ACCESS_TOKEN",},
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
                    "description": "Asana workspace GID (numeric string) where the task will be created",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the task",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes or description for the task",
                },
                "assignee": {
                    "type": "string",
                    "description": "User GID to assign the task to",
                },
                "due_on": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
            },
            "required": ["workspace", "name"],
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
        
        url = "https://app.asana.com/api/1.0/tasks"
        
        task_data: Dict[str, Any] = {
            "name": parameters["name"],
            "workspace": parameters["workspace"],
        }
        notes = parameters.get("notes")
        if notes:
            task_data["notes"] = notes
        assignee = parameters.get("assignee")
        if assignee:
            task_data["assignee"] = assignee
        due_on = parameters.get("due_on")
        if due_on:
            task_data["due_on"] = due_on
        
        body = {"data": task_data}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_text = response.text
                    error_msg = f"Asana API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            asana_error = errors[0]
                            error_msg = asana_error.get("message", error_msg)
                            help_text = asana_error.get("help")
                            if help_text:
                                error_msg += f" ({help_text})"
                    except Exception:
                        error_msg = error_text or error_msg
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")