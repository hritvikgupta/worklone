from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class AsanaSearchTasksTool(BaseTool):
    name = "asana_search_tasks"
    description = "Search for tasks in an Asana workspace"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASANA_ACCESS_TOKEN",
                description="OAuth access token for Asana",
                env_var="ASANA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "asana",
            context=context,
            context_token_keys=("asana_token",),
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
                    "description": "Asana workspace GID (numeric string) to search tasks in",
                },
                "text": {
                    "type": "string",
                    "description": "Text to search for in task names",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter tasks by assignee user GID",
                },
                "projects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of Asana project GIDs (numeric strings) to filter tasks by",
                },
                "completed": {
                    "type": "boolean",
                    "description": "Filter by completion status",
                },
            },
            "required": ["workspace"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        workspace = parameters["workspace"]
        params: Dict[str, str] = {}
        text = parameters.get("text")
        if text:
            params["text"] = text
        assignee = parameters.get("assignee")
        if assignee:
            params["assignee.any"] = assignee
        projects = parameters.get("projects", [])
        if projects:
            params["projects.any"] = ",".join(str(p) for p in projects)
        completed = parameters.get("completed")
        if completed is not None:
            params["completed"] = str(completed).lower()
        params["opt_fields"] = "gid,name,notes,completed,assignee,assignee.name,due_on,created_at,modified_at,created_by,created_by.name,resource_type,resource_subtype"
        
        url = f"https://app.asana.com/api/1.0/workspaces/{workspace}/tasks/search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    tasks_mapped = []
                    for task in data.get("data", []):
                        assignee_obj = None
                        assignee = task.get("assignee")
                        if assignee:
                            assignee_obj = {
                                "gid": assignee["gid"],
                                "name": assignee["name"],
                            }
                        created_by_obj = None
                        created_by = task.get("created_by")
                        if created_by:
                            created_by_obj = {
                                "gid": created_by["gid"],
                                "resource_type": created_by.get("resource_type"),
                                "name": created_by["name"],
                            }
                        tasks_mapped.append({
                            "gid": task["gid"],
                            "resource_type": task.get("resource_type"),
                            "resource_subtype": task.get("resource_subtype"),
                            "name": task["name"],
                            "notes": task.get("notes", ""),
                            "completed": task.get("completed", False),
                            "assignee": assignee_obj,
                            "created_by": created_by_obj,
                            "due_on": task.get("due_on"),
                            "created_at": task.get("created_at"),
                            "modified_at": task.get("modified_at"),
                        })
                    transformed = {
                        "success": True,
                        "ts": datetime.utcnow().isoformat(),
                        "tasks": tasks_mapped,
                        "next_page": data.get("next_page"),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed, default=str),
                        data=transformed,
                    )
                else:
                    error_text = response.text
                    error_message = f"Asana API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            asana_error = errors[0]
                            error_message = asana_error.get("message", error_message)
                            help_text = asana_error.get("help")
                            if help_text:
                                error_message += f" ({help_text})"
                    except json.JSONDecodeError:
                        error_message += f": {error_text}"
                    return ToolResult(success=False, output="", error=error_message)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")