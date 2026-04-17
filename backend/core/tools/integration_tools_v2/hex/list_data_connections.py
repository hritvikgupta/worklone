from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HexListDataConnectionsTool(BaseTool):
    name = "hex_list_data_connections"
    description = "List all data connections in the Hex workspace (e.g., Snowflake, PostgreSQL, BigQuery)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HEX_API_KEY",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        access_token = context.get("HEX_API_KEY") if context else ""
        if self._is_placeholder_token(access_token):
            return ""
        return access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of connections to return (1-500, default: 25)",
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
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://app.hex.tech/api/v1/data-connections"
        query_params: dict[str, Any] = {}
        for key in ["limit", "sortBy", "sortDirection"]:
            value = parameters.get(key)
            if value is not None:
                query_params[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    resp_data = response.json()
                    connections = resp_data if isinstance(resp_data, list) else (resp_data.get("values", []) if isinstance(resp_data, dict) else [])
                    transformed_connections = []
                    for c in connections:
                        transformed_connections.append({
                            "id": c.get("id"),
                            "name": c.get("name"),
                            "type": c.get("type"),
                            "description": c.get("description"),
                            "connectViaSsh": c.get("connectViaSsh"),
                            "includeMagic": c.get("includeMagic"),
                            "allowWritebackCells": c.get("allowWritebackCells"),
                        })
                    output_data = {
                        "connections": transformed_connections,
                        "total": len(transformed_connections),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")