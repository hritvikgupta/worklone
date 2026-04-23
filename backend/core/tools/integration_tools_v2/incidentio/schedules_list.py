from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioSchedulesListTool(BaseTool):
    name = "incidentio_schedules_list"
    description = "List all schedules in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        token = context.get("api_key") if context else None
        if self._is_placeholder_token(token or ""):
            token = os.environ.get("INCIDENTIO_API_KEY")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "number",
                    "description": "Number of results per page (e.g., 10, 25, 50). Default: 25",
                },
                "after": {
                    "type": "string",
                    "description": 'Pagination cursor to fetch the next page of results (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.incident.io/v2/schedules"
        query_params: Dict[str, Any] = {}
        if parameters.get("page_size") is not None:
            query_params["page_size"] = parameters["page_size"]
        if parameters.get("after") is not None:
            query_params["after"] = parameters["after"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")