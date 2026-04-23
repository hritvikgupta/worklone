from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListFlowsTool(BaseTool):
    name = "gong_list_flows"
    description = "List Gong Engage flows (sales engagement sequences)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKey",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="accessKeySecret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "flowOwnerEmail": {
                    "type": "string",
                    "description": "Email of a Gong user. The API will return 'PERSONAL' flows belonging to this user in addition to 'COMPANY' flows.",
                },
                "workspaceId": {
                    "type": "string",
                    "description": "Optional workspace ID to filter flows to a specific workspace",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous API call to retrieve the next page of records",
                },
            },
            "required": ["flowOwnerEmail"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("accessKey") if context else None
        access_key_secret = context.get("accessKeySecret") if context else None
        
        if not access_key or not access_key_secret or self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access credentials not configured.")
        
        auth_str = base64.b64encode(f"{access_key}:{access_key_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_str}",
        }
        
        url = "https://api.gong.io/v2/flows"
        
        params_dict = {
            "flowOwnerEmail": parameters["flowOwnerEmail"],
        }
        if parameters.get("workspaceId"):
            params_dict["workspaceId"] = parameters["workspaceId"]
        if parameters.get("cursor"):
            params_dict["cursor"] = parameters["cursor"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")