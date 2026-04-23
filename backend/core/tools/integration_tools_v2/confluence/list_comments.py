from typing import Any, Dict
import httpx
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListCommentsTool(BaseTool):
    name = "confluence_list_comments"
    description = "List all comments on a Confluence page."
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
                "pageId": {
                    "type": "string",
                    "description": "Confluence page ID to list comments from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of comments to return (default: 25)",
                },
                "bodyFormat": {
                    "type": "string",
                    "description": "Format for the comment body: storage, atlas_doc_format, view, or export_view (default: storage)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
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
        
        domain: str = parameters["domain"]
        page_id: str = parameters["pageId"]
        limit: int = int(parameters.get("limit", 25))
        body_format: str = parameters.get("bodyFormat", "storage")
        cursor: str | None = parameters.get("cursor")
        cloud_id: str | None = parameters.get("cloudId")
        
        expand = f"body.{body_format}"
        query_params: dict[str, Any] = {
            "limit": limit,
            "expand": expand,
        }
        if cursor:
            query_params["cursor"] = cursor
        
        if cloud_id:
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages/{page_id}/comments"
        else:
            url = f"https://{domain}/wiki/api/v2/pages/{page_id}/comments"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    comments = []
                    for comment in data.get("results", []):
                        body = comment.get("body", {})
                        body_str = body.get("value", "") if isinstance(body, dict) else ""
                        author = comment.get("author", {})
                        author_id = author.get("accountId", "") if isinstance(author, dict) else ""
                        comments.append({
                            "id": comment.get("id", ""),
                            "body": body_str,
                            "createdAt": comment.get("createdAt", ""),
                            "authorId": author_id,
                        })
                    next_cursor = None
                    links = data.get("_links", {})
                    if isinstance(links, dict) and "next" in links:
                        next_url = links["next"]
                        parsed = urlparse(next_url)
                        qs = parse_qs(parsed.query)
                        next_cursor = qs.get("cursor", [None])[0]
                    output = {
                        "ts": datetime.utcnow().isoformat(),
                        "comments": comments,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(success=True, output=json.dumps(output), data=output)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")