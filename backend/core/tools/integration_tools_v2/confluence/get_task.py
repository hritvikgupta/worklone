from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetTaskTool(BaseTool):
    name = "confluence_get_task"
    description = "Get a specific Confluence inline task by ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="OAuth access token for Confluence",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to retrieve",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "taskId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        task_id = parameters["taskId"]
        cloud_id = parameters.get("cloudId")
        
        if cloud_id:
            url = f"https://api.atlassian.com/confluence/cloud/{cloud_id}/wiki/rest/api/inlinetask/{task_id}"
        else:
            url = f"https://{domain}.atlassian.net/wiki/rest/api/inlinetask/{task_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    task = data.get("task") or data
                    container_content = task.get("container", {}).get("content", {})
                    content_type = container_content.get("type")
                    content_id = container_content.get("id")
                    space_id = task.get("spaceId") or container_content.get("space", {}).get("id")
                    page_id = task.get("pageId") or (content_id if content_type == "page" else None)
                    blog_post_id = task.get("blogPostId") or (content_id if content_type == "blogpost" else None)
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "id": task.get("id") or "",
                        "localId": task.get("localId"),
                        "spaceId": space_id,
                        "pageId": page_id,
                        "blogPostId": blog_post_id,
                        "status": task.get("status") or "",
                        "body": task.get("body") or task.get("text"),
                        "createdBy": task.get("createdBy") or task.get("creator", {}).get("accountId"),
                        "assignedTo": task.get("assignedTo") or (task.get("assignee", {}).get("accountId") if task.get("assignee") else None),
                        "completedBy": task.get("completedBy"),
                        "createdAt": task.get("createdAt"),
                        "updatedAt": task.get("updatedAt"),
                        "dueAt": task.get("dueAt") or task.get("dueDate"),
                        "completedAt": task.get("completedAt") or task.get("completedDate"),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")