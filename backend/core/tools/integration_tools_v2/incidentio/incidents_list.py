from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentsListTool(BaseTool):
    name = "incident_io_incidents_list"
    description = "List incidents from incident.io. Returns a list of incidents with their details including severity, status, and timestamps."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        if context is None:
            return ""
        access_token = context.get("INCIDENTIO_API_KEY")
        return access_token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "number",
                    "description": "Number of incidents to return per page (e.g., 10, 25, 50). Default: 25",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor to fetch the next page of results (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.incident.io/v2/incidents"
        query_params = {}
        page_size = parameters.get("page_size")
        if page_size is not None:
            query_params["page_size"] = page_size
        after = parameters.get("after")
        if after is not None:
            query_params["after"] = after
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")