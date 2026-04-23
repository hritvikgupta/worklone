from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeleteBlogPostTool(BaseTool):
    name = "confluence_delete_blogpost"
    description = "Delete a Confluence blog post."
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
                "blogPostId": {
                    "type": "string",
                    "description": "The ID of the blog post to delete",
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
        
        domain = parameters["domain"]
        blog_post_id = parameters["blogPostId"]
        cloud_id = parameters.get("cloudId")

        headers_auth = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        if not cloud_id:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        "https://api.atlassian.com/oauth/token/accessible-resources",
                        headers=headers_auth,
                    )
                    if resp.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to fetch accessible resources: {resp.text}",
                        )
                    sites: list[dict] = resp.json()
                    expected_url = f"https://{domain}/wiki"
                    for site in sites:
                        if site.get("url") == expected_url:
                            cloud_id = site["id"]
                            break
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error="Could not determine cloudId from accessible resources for the given domain.",
                        )
            except Exception as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Error fetching cloudId: {str(e)}",
                )

        url = f"https://{domain}/wiki/rest/api/content/{blog_post_id}"
        headers = headers_auth.copy()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {
                        "ts": ts,
                        "blogPostId": blog_post_id,
                        "deleted": True,
                    }
                    return ToolResult(
                        success=True,
                        output=str(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")