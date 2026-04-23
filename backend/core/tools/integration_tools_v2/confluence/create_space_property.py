from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceCreateSpacePropertyTool(BaseTool):
    name = "confluence_create_space_property"
    description = "Create a property on a Confluence space."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="Access token",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            site_user_url = f"https://{domain}/wiki/rest/api/user/current"
            resp = await client.get(site_user_url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Access token invalid for domain {domain}: HTTP {resp.status_code}")
            userinfo_url = "https://api.atlassian.com/oauth/token/userinfo"
            resp = await client.get(userinfo_url, headers=headers)
            if resp.status_code != 200:
                raise ValueError("Failed to fetch userinfo")
            data = resp.json()
            cloud_id = None
            for account in data.get("accounts", []):
                products = account.get("product", [])
                if isinstance(products, list):
                    for prod in products:
                        if prod.get("id") == "confluence":
                            cloud_id = account.get("cloud_id")
                            break
                if cloud_id:
                    break
            if not cloud_id:
                raise ValueError("No Confluence Cloud ID found in userinfo")
            return cloud_id

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "spaceId": {
                    "type": "string",
                    "description": "Space ID to create the property on",
                },
                "key": {
                    "type": "string",
                    "description": "Property key/name",
                },
                "value": {
                    "type": "object",
                    "description": "Property value (JSON)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceId", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        space_id = parameters["spaceId"]
        key = parameters["key"]
        value = parameters.get("value", {})
        cloud_id = parameters.get("cloudId")
        
        if not cloud_id:
            try:
                cloud_id = await self._get_cloud_id(access_token, domain)
            except ValueError as e:
                return ToolResult(success=False, output="", error=str(e))
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/spaces/{space_id}/properties"
        body = {
            "key": key,
            "value": value,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")