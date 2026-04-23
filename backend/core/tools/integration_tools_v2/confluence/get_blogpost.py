from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetBlogPostTool(BaseTool):
    name = "confluence_get_blogpost"
    description = "Get a specific Confluence blog post by ID, including its content."
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
            context_token_keys=("confluence_token",),
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
                "blogPostId": {
                    "type": "string",
                    "description": "The ID of the blog post to retrieve",
                },
                "bodyFormat": {
                    "type": "string",
                    "description": "Format for blog post body: storage, atlas_doc_format, or view",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "blogPostId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        blog_post_id: str = parameters["blogPostId"].strip()
        body_format: str = parameters.get("bodyFormat", "storage")
        cloud_id: str | None = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if not cloud_id:
                    site_list_url = "https://api.atlassian.com/ex/confluence/me/api/site"
                    site_resp = await client.get(site_list_url, headers=headers)
                    if site_resp.status_code != 200:
                        return ToolResult(success=False, output="", error=f"Failed to fetch sites: {site_resp.text}")
                    sites: list[dict[str, Any]] = site_resp.json()
                    cloud_id = None
                    expected_url = f"https://{domain}/wiki"
                    for site in sites:
                        site_url = site.get("url", "")
                        if site_url == expected_url:
                            cloud_id = site["id"]
                            break
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Could not determine cloudId for domain '{domain}'.",
                        )
                
                content_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/rest/api/content/{blog_post_id}"
                params_dict = {"expand": f"body.{body_format},version,space,author"}
                
                response = await client.get(content_url, headers=headers, params=params_dict)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")