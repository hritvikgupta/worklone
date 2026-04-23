from typing import Any, Dict
import httpx
from datetime import datetime
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceRetrieveTool(BaseTool):
    name = "confluence_retrieve"
    description = "Retrieve content from Confluence pages using the Confluence API."
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
            context_token_keys=("provider_token",},
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",},
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
                    "description": "Confluence page ID to retrieve (numeric ID from page URL or API)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId"],
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
        page_id = parameters.get("pageId", "").strip()
        cloud_id = parameters.get("cloudId")
        
        if not domain or not page_id:
            return ToolResult(success=False, output="", error="Missing required parameters: domain and pageId.")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch cloud ID if not provided
                if not cloud_id:
                    resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                    response = await client.get(resources_url, headers=headers)
                    if response.status_code not in [200]:
                        return ToolResult(success=False, output="", error=response.text)
                    resources = response.json()
                    cloud_id = None
                    for resource in resources:
                        resource_url = resource.get("url", "").rstrip("/")
                        if resource_url.endswith(domain):
                            cloud_id = resource["id"]
                            break
                    if not cloud_id:
                        return ToolResult(success=False, output="", error=f"Could not find Confluence Cloud ID for domain '{domain}'.")
                
                # Retrieve page content
                content_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/rest/api/content/{page_id}"
                params = {
                    "expand": "body.view,body.storage,version,history,container,metadata.labels",
                }
                response = await client.get(content_url, headers=headers, params=params)
                
                if response.status_code in [200]:
                    data = response.json()
                    # Basic transform to match expected outputs
                    transformed = {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "pageId": data.get("id"),
                        "title": data.get("title", ""),
                        "status": data.get("status"),
                        "spaceId": data.get("space", {}).get("id"),
                        "parentId": data.get("container", {}).get("id"),
                        "authorId": data.get("history", {}).get("createdBy", {}).get("accountId"),
                        "createdAt": data.get("history", {}).get("createdDate"),
                        "url": data.get("_links", {}).get("webui"),
                    }
                    body = data.get("body", {})
                    view_value = body.get("view", {}).get("value", "")
                    transformed["content"] = re.sub(r"<[^>]+>", "", view_value)
                    storage = body.get("storage", {})
                    if storage:
                        transformed["body"] = {"storage": storage}
                    version = data.get("version")
                    if version:
                        transformed["version"] = version
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")