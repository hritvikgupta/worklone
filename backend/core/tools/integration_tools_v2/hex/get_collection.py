from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HexGetCollectionTool(BaseTool):
    name = "hex_get_collection"
    description = "Retrieve details for a specific Hex collection by its ID."
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
                "collectionId": {
                    "type": "string",
                    "description": "The UUID of the collection",
                },
            },
            "required": ["collectionId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        hex_api_key = context.get("hex_api_key") if context else None
        
        if self._is_placeholder_token(hex_api_key):
            return ToolResult(success=False, output="", error="Hex API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {hex_api_key}",
            "Content-Type": "application/json",
        }
        
        url = f"https://app.hex.tech/api/v1/collections/{parameters['collectionId']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")