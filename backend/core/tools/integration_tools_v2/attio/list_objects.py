from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListObjectsTool(BaseTool):
    name = "attio_list_objects"
    description = "List all objects (system and custom) in the Attio workspace"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="The OAuth access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = "https://api.attio.com/v2/objects"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                try:
                    data = response.json()
                except:
                    data = {}
                
                if response.status_code >= 400:
                    error_msg = data.get("message") or response.text or "Failed to list objects"
                    return ToolResult(success=False, output="", error=error_msg)
                
                objects = [
                    {
                        "objectId": obj.get("id", {}).get("object_id"),
                        "apiSlug": obj.get("api_slug"),
                        "singularNoun": obj.get("singular_noun"),
                        "pluralNoun": obj.get("plural_noun"),
                        "createdAt": obj.get("created_at"),
                    }
                    for obj in data.get("data", [])
                ]
                transformed = {
                    "objects": objects,
                    "count": len(objects),
                }
                output = json.dumps(transformed)
                return ToolResult(success=True, output=output, data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")