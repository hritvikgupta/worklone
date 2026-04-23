from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceCreatePagePropertyTool(BaseTool):
    name = "confluence_create_page_property"
    description = "Create a new custom property (metadata) on a Confluence page."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="OAuth access token for Confluence",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "pageId": {
                    "type": "string",
                    "description": "The ID of the page to add the property to",
                },
                "key": {
                    "type": "string",
                    "description": "The key/name for the property",
                },
                "value": {
                    "type": "object",
                    "description": "The value for the property (can be any JSON value)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId", "key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        domain = parameters["domain"]
        page_id = parameters["pageId"].strip()
        prop_key = parameters["key"]
        value = parameters["value"]
        cloud_id = parameters.get("cloudId")
        
        if not cloud_id:
            tenant_url = f"https://{domain}.atlassian.net/_edge/tenant-info"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    tenant_resp = await client.get(tenant_url)
                    if tenant_resp.status_code == 200:
                        tenant_data = tenant_resp.json()
                        cloud_id = tenant_data.get("cloudId")
                        if not cloud_id:
                            return ToolResult(success=False, output="", error="Could not fetch cloudId from tenant info.")
                    else:
                        return ToolResult(success=False, output="", error=f"Failed to fetch tenant info: {tenant_resp.status_code}")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Failed to resolve cloudId: {str(e)}")
        
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/content/{page_id}/property"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={"key": prop_key, "value": value})
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "pageId": page_id,
                        "propertyId": data.get("id", ""),
                        "key": data.get("key", prop_key),
                        "value": data.get("value", value),
                        "version": data.get("version"),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")