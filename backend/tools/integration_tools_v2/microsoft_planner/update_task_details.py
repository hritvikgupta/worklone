from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerUpdateTaskDetailsTool(BaseTool):
    name = "microsoft_planner_update_task_details"
    description = "Update task details including description, checklist items, and references in Microsoft Planner"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _clean_etag(self, etag: str) -> str:
        cleaned = etag.strip()
        while cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        if '\\"' in cleaned:
            cleaned = cleaned.replace('\\"', '"')
        return cleaned

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_PLANNER_ACCESS_TOKEN",
                description="Access token for the Microsoft Planner API",
                env_var="MICROSOFT_PLANNER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-planner",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_PLANNER_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task (e.g., \"pbT5K2OVkkO1M7r5bfsJ6JgAGD5m\")",
                },
                "etag": {
                    "type": "string",
                    "description": "The ETag value from the task details to update (If-Match header)",
                },
                "description": {
                    "type": "string",
                    "description": "The description of the task",
                },
                "checklist": {
                    "type": "object",
                    "description": "Checklist items as a JSON object",
                },
                "references": {
                    "type": "object",
                    "description": "References as a JSON object",
                },
                "previewType": {
                    "type": "string",
                    "description": "Preview type: automatic, noPreview, checklist, description, or reference",
                },
            },
            "required": ["taskId", "etag"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        task_id = parameters.get("taskId")
        if not task_id:
            return ToolResult(success=False, output="", error="Task ID is required")
        
        etag = parameters.get("etag")
        if not etag:
            return ToolResult(success=False, output="", error="ETag is required")
        
        cleaned_etag = self._clean_etag(etag)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
            "If-Match": cleaned_etag,
        }
        
        body: Dict[str, Any] = {}
        description = parameters.get("description")
        if description is not None:
            body["description"] = description
        checklist = parameters.get("checklist")
        if checklist is not None:
            body["checklist"] = checklist
        references = parameters.get("references")
        if references is not None:
            body["references"] = references
        preview_type = parameters.get("previewType")
        if preview_type is not None:
            body["previewType"] = preview_type
        
        if len(body) == 0:
            return ToolResult(success=False, output="", error="At least one field must be provided to update")
        
        url = f"https://graph.microsoft.com/v1.0/planner/tasks/{task_id}/details"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")