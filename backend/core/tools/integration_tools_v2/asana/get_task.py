from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token
from urllib.parse import urlencode

class AsanaGetTaskTool(BaseTool):
    name = "asana_get_task"
    description = "Retrieve a single task by GID or get multiple tasks with filters"
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
            context_token_keys=("accessToken",),
            env_token_keys=("ASANA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _format_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        assignee = task.get("assignee")
        if assignee:
            assignee = {
                "gid": assignee["gid"],
                "name": assignee["name"],
            }
        created_by = task.get("created_by")
        if created_by:
            created_by = {
                "gid": created_by["gid"],
                "name": created_by["name"],
                "resource_type": created_by.get("resource_type"),
            }
        return {
            "gid": task["gid"],
            "resource_type": task["resource_type"],
            "resource_subtype": task["resource_subtype"],
            "name": task["name"],
            "notes": task.get("notes", ""),
            "completed": task.get("completed", False),
            "assignee": assignee,
            "created_by": created_by,
            "due_on": task.get("due_on"),
            "created_at": task["created_at"],
            "modified_at": task["modified_at"],
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskGid": {
                    "type": "string",
                    "description": "The globally unique identifier (GID) of the task. If not provided, will get multiple tasks.",
                },
                "workspace": {
                    "type": "string",
                    "description": "Asana workspace GID (numeric string) to filter tasks (required when not using taskGid)",
                },
                "project": {
                    "type": "string",
                    "description": "Asana project GID (numeric string) to filter tasks",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of tasks to return (default: 50)",
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
            "Accept": "application/json",
        }
        
        task_gid = parameters.get("taskGid")
        workspace = parameters.get("workspace")
        project = parameters.get("project")
        
        try:
            limit_val = int(parameters.get("limit", 50))
        except (ValueError, TypeError):
            limit_val = 50
        
        opt_fields = "gid,name,notes,completed,assignee,assignee.name,due_on,created_at,modified_at,created_by,created_by.name,resource_type,resource_subtype"
        
        if task_gid:
            url = f"https://app.asana.com/api/1.0/tasks/{task_gid}"
            params: dict = {"opt_fields": opt_fields}
            list_mode = False
        else:
            if not workspace and not project:
                return ToolResult(
                    success=False,
                    output="",
                    error="Either taskGid or workspace/project must be provided",
                )
            params = {"opt_fields": opt_fields, "limit": str(limit_val)}
            if project:
                params["project"] = project
            elif workspace:
                params["workspace"] = workspace
            url = "https://app.asana.com/api/1.0/tasks"
            list_mode = True
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    ts = datetime.now(timezone.utc).isoformat()
                    if list_mode:
                        tasks = [
                            self._format_task(task)
                            for task in data.get("data", [])
                        ]
                        result = {
                            "success": True,
                            "ts": ts,
                            "tasks": tasks,
                            "next_page": data.get("next_page"),
                        }
                    else:
                        task = self._format_task(data["data"])
                        result = {
                            "success": True,
                            "ts": ts,
                            **task,
                        }
                    return ToolResult(success=True, output=json.dumps(result), data=result)
                else:
                    error_text = response.text
                    error_message = f"Asana API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            asana_error = errors[0]
                            msg = asana_error.get("message")
                            if msg:
                                error_message = f"{msg} ({asana_error.get('help', '')})"
                    except:
                        pass
                    return ToolResult(success=False, output=error_text, error=error_message)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")