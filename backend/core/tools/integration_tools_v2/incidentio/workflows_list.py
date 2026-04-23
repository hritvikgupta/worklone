from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioWorkflowsListTool(BaseTool):
    name = "incidentio_workflows_list"
    description = "List all workflows in your incident.io workspace."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_API_KEY",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "number",
                    "description": "Number of workflows to return per page (e.g., 10, 25, 50)",
                },
                "after": {
                    "type": "string",
                    "description": 'Pagination cursor to fetch the next page of results (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("INCIDENTIO_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = "https://api.incident.io/v2/workflows"
        params: Dict[str, Any] = {}
        if "page_size" in parameters:
            params["page_size"] = parameters["page_size"]
        if "after" in parameters:
            params["after"] = parameters["after"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    workflows = []
                    for workflow in data.get("workflows", []):
                        workflows.append({
                            "id": workflow.get("id"),
                            "name": workflow.get("name"),
                            "state": workflow.get("state"),
                            "folder": workflow.get("folder"),
                            "created_at": workflow.get("created_at"),
                            "updated_at": workflow.get("updated_at"),
                        })
                    transformed: Dict[str, Any] = {"workflows": workflows}
                    pagination_meta = data.get("pagination_meta")
                    if pagination_meta:
                        transformed["pagination_meta"] = {
                            "after": pagination_meta.get("after"),
                            "page_size": pagination_meta.get("page_size"),
                        }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")