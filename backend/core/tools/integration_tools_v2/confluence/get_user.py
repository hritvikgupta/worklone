from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetUserTool(BaseTool):
    name = "confluence_get_user"
    description = "Get display name and profile info for a Confluence user by account ID."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "accountId": {
                    "type": "string",
                    "description": "The Atlassian account ID of the user to look up",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "accountId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        domain = parameters.get("domain", "").strip()
        account_id = parameters.get("accountId", "").strip()
        cloud_id = parameters.get("cloudId", "").strip()
        
        if not domain:
            return ToolResult(success=False, output="", error="Domain is required.")
        if not account_id:
            return ToolResult(success=False, output="", error="Account ID is required.")
        
        if not cloud_id:
            accessible_url = "https://api.atlassian.com/oauth/token/accessible-resources"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(accessible_url, headers=headers)
                    if resp.status_code != 200:
                        return ToolResult(success=False, output="", error=f"Failed to fetch accessible resources: {resp.text}")
                    resources: list[dict] = resp.json()
                    for resource in resources:
                        resource_url = resource.get("url", "").rstrip("/")
                        if resource_url.startswith(f"https://{domain}"):
                            cloud_id = resource["id"]
                            break
                    if not cloud_id:
                        return ToolResult(success=False, output="", error=f"No matching cloud ID found for domain '{domain}'")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Error fetching cloud ID: {str(e)}")
        
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/user?accountId={account_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")