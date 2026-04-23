from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetSpaceTool(BaseTool):
    name = "confluence_get_space"
    description = "Get details about a specific Confluence space."
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
                "spaceId": {
                    "type": "string",
                    "description": "Confluence space ID to retrieve",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        domain = parameters["domain"]
        space_id = parameters["spaceId"]
        cloud_id = parameters.get("cloudId")
        
        client = httpx.AsyncClient(timeout=30.0)
        try:
            if not cloud_id:
                acc_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                acc_response = await client.get(acc_url, headers=headers)
                
                if acc_response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"Failed to resolve cloudId: {acc_response.text}")
                
                resources = acc_response.json()
                cloud_id = None
                for resource in resources:
                    resource_url = resource.get("url", "")
                    if resource_url == f"https://{domain}/wiki":
                        cloud_id = resource["id"]
                        break
                
                if not cloud_id:
                    return ToolResult(success=False, output="", error=f"Could not find cloudId for domain '{domain}'. Check accessible resources.")
            
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/space/{space_id}"
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                transformed = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "spaceId": data.get("id"),
                    "name": data.get("name"),
                    "key": data.get("key"),
                    "type": data.get("type"),
                    "status": data.get("status"),
                    "url": data.get("_links", {}).get("webui", ""),
                    "authorId": data.get("_creator", {}).get("accountId"),
                    "createdAt": data.get("history", {}).get("createdDate"),
                    "homepageId": data.get("homepage", {}).get("id"),
                    "description": data.get("description"),
                }
                return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
            else:
                return ToolResult(success=False, output="", error=response.text)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
        finally:
            await client.aclose()