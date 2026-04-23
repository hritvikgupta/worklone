from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListUsersTool(BaseTool):
    name = "ashby_list_users"
    description = "Lists all users in Ashby with pagination."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ASHBY_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/user.list"
        body: Dict[str, Any] = {}
        if parameters.get("cursor"):
            body["cursor"] = parameters["cursor"]
        if parameters.get("perPage"):
            body["limit"] = parameters["perPage"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    error_info = data.get("errorInfo", {})
                    error_msg = error_info.get("message") if isinstance(error_info, dict) else str(error_info) if error_info else "Failed to list users"
                    return ToolResult(success=False, output="", error=error_msg)
                
                users = []
                for u in data.get("results", []):
                    users.append({
                        "id": u.get("id"),
                        "firstName": u.get("firstName"),
                        "lastName": u.get("lastName"),
                        "email": u.get("email"),
                        "isEnabled": u.get("isEnabled", False),
                        "globalRole": u.get("globalRole"),
                    })
                
                transformed = {
                    "users": users,
                    "moreDataAvailable": data.get("moreDataAvailable", False),
                    "nextCursor": data.get("nextCursor"),
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(transformed),
                    data=transformed,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")