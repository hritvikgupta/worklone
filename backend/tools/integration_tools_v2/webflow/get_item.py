from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WebflowGetItemTool(BaseTool):
    name = "webflow_get_item"
    description = "Get a single item from a Webflow CMS collection"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WEBFLOW_ACCESS_TOKEN",
                description="Access token",
                env_var="WEBFLOW_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "webflow",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("WEBFLOW_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "siteId": {
                    "type": "string",
                    "description": 'ID of the Webflow site (e.g., "580e63e98c9a982ac9b8b741")',
                },
                "collectionId": {
                    "type": "string",
                    "description": 'ID of the collection (e.g., "580e63fc8c9a982ac9b8b745")',
                },
                "itemId": {
                    "type": "string",
                    "description": 'ID of the item to retrieve (e.g., "580e64008c9a982ac9b8b754")',
                },
            },
            "required": ["siteId", "collectionId", "itemId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        collection_id = parameters["collectionId"]
        item_id = parameters["itemId"]
        url = f"https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")