from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ConfluenceUpdateBlogPostTool(BaseTool):
    name = "confluence_update_blogpost"
    description = "Update an existing Confluence blog post title and/or content."
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
            ),
            CredentialRequirement(
                key="CONFLUENCE_DOMAIN",
                description="Your Confluence domain (e.g., yourcompany.atlassian.net)",
                env_var="CONFLUENCE_DOMAIN",
                required=True,
                auth_type="text",
            ),
            CredentialRequirement(
                key="CONFLUENCE_CLOUD_ID",
                description="Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                env_var="CONFLUENCE_CLOUD_ID",
                required=False,
                auth_type="text",
            ),
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

    def _resolve_domain(self, context: dict | None) -> str:
        domain = context.get("CONFLUENCE_DOMAIN") if context else None
        if self._is_placeholder_token(domain or ""):
            raise ValueError("Confluence domain not configured.")
        return domain.strip()

    async def _resolve_cloud_id(self, context: dict | None, access_token: str, domain: str) -> str:
        cloud_id = context.get("CONFLUENCE_CLOUD_ID") if context else None
        if cloud_id and not self._is_placeholder_token(cloud_id):
            return cloud_id.strip()
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers=headers,
            )
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources: {resp.status_code} {resp.text}")
            sites = resp.json()
            target_url = f"https://{domain}/wiki"
            for site in sites:
                if site.get("url") == target_url:
                    return site["id"]
            raise ValueError(f"No matching site found for domain '{domain}'")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "blogPostId": {
                    "type": "string",
                    "description": "The ID of the blog post to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the blog post",
                },
                "content": {
                    "type": "string",
                    "description": "New content for the blog post in storage format",
                },
            },
            "required": ["blogPostId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token = await self._resolve_access_token(context)
            if self._is_placeholder_token(access_token):
                return ToolResult(success=False, output="", error="Access token not configured.")

            domain = self._resolve_domain(context)
            cloud_id = await self._resolve_cloud_id(context, access_token, domain)

            blog_post_id = parameters["blogPostId"]
            title = parameters.get("title")
            content = parameters.get("content")

            api_base = f"https://api.atlassian.com/ex/confluence/{cloud_id}/rest/v1"
            url = f"{api_base}/content/{blog_post_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch blog post: HTTP {resp.status_code} - {resp.text}",
                    )

                current = resp.json()
                if current.get("type") != "blogpost":
                    return ToolResult(
                        success=False, output="", error="The specified ID does not refer to a blog post."
                    )

                current_title = current.get("title", "")
                body = current.get("body", {})
                if body.get("representation") != "storage":
                    return ToolResult(
                        success=False,
                        output="",
                        error="Blog post body is not available in storage format.",
                    )
                current_content = body["storage"].get("value", "")

                new_title = title if title is not None else current_title
                new_content = content if content is not None else current_content
                version_number = current["version"]["number"] + 1

                update_body = {
                    "id": blog_post_id,
                    "type": "blogpost",
                    "title": new_title,
                    "body": {
                        "representation": "storage",
                        "value": new_content,
                    },
                    "version": {
                        "number": version_number,
                    },
                }

                resp = await client.put(url, headers=headers, json=update_body)
                if resp.status_code not in [200, 201]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to update blog post: HTTP {resp.status_code} - {resp.text}",
                    )

                data = resp.json()
                output_dict = {
                    "ts": datetime.utcnow().isoformat(),
                    "blogPostId": data.get("id", blog_post_id),
                    "title": data.get("title", new_title),
                    "status": data.get("status"),
                    "spaceId": data.get("space", {}).get("id"),
                    "version": data.get("version"),
                    "url": data.get("_links", {}).get("webui", ""),
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_dict),
                    data=output_dict,
                )

        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")