import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListDepartmentsTool(BaseTool):
    name = "ashby_list_departments"
    description = "Lists all departments in Ashby."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        return context.get("ASHBY_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
        }
        
        url = "https://api.ashbyhq.com/department.list"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list departments")
                    return ToolResult(success=False, output="", error=error_msg)
                
                departments = [
                    {
                        "id": d.get("id"),
                        "name": d.get("name"),
                        "isArchived": d.get("isArchived", False),
                        "parentId": d.get("parentId"),
                    }
                    for d in data.get("results", [])
                ]
                
                output_data = {"departments": departments}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")