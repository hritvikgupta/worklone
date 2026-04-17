from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HexListGroupsTool(BaseTool):
    name = "hex_list_groups"
    description = "List all groups in the Hex workspace with optional sorting."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="hex_api_key",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of groups to return (1-500, default: 25)",
                },
                "sortBy": {
                    "type": "string",
                    "description": "Sort by field: CREATED_AT or NAME",
                },
                "sortDirection": {
                    "type": "string",
                    "description": "Sort direction: ASC or DESC",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("hex_api_key") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Hex API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        base_url = "https://app.hex.tech/api/v1/groups"
        params: Dict[str, Any] = {}
        for key in ["limit", "sortBy", "sortDirection"]:
            value = parameters.get(key)
            if value is not None:
                params[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    groups = data if isinstance(data, list) else data.get("values", [])
                    processed_groups = [
                        {
                            "id": g.get("id"),
                            "name": g.get("name"),
                            "createdAt": g.get("createdAt"),
                        }
                        for g in groups
                    ]
                    result = {
                        "groups": processed_groups,
                        "total": len(processed_groups),
                    }
                    return ToolResult(success=True, output=json.dumps(result), data=result)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")