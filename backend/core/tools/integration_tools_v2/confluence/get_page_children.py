from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetPageChildrenTool(BaseTool):
    name = "confluence_get_page_children"
    description = "Get all child pages of a specific Confluence page. Useful for navigating page hierarchies."
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
            context_token_keys=("confluence_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _extract_next_cursor(self, next_link: str | None) -> str | None:
        if not next_link:
            return None
        try:
            parsed = urlparse(next_link)
            return parse_qs(parsed.query).get("cursor", [None])[0]
        except Exception:
            return None

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pageId": {
                    "type": "string",
                    "description": "The ID of the parent page to get children from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of child pages to return (default: 50, max: 250)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response to get the next page of results",
                },
            },
            "required": ["pageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        domain = (context or {}).get("domain")
        cloud_id = (context or {}).get("cloudId")

        if not domain:
            return ToolResult(success=False, output="", error="Confluence domain not provided in context.")

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        page_id = str(parameters.get("pageId", "")).strip()
        if not page_id:
            return ToolResult(success=False, output="", error="pageId is required.")

        limit_raw = parameters.get("limit")
        limit = 50
        if limit_raw is not None:
            limit = max(1, min(250, int(float(limit_raw))))

        cursor = parameters.get("cursor")

        if cloud_id:
            base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id.strip()}/wiki/api/v2"
        else:
            base_url = f"https://{domain.strip()}.atlassian.net/wiki/api/v2"
        url = f"{base_url}/pages/{page_id}/children"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        params: Dict[str, Any] = {
            "page_size": limit,
        }
        if cursor:
            params["cursor"] = cursor

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    children = []
                    for page in results:
                        children.append({
                            "id": page.get("id"),
                            "title": page.get("title"),
                            "status": page.get("status"),
                            "spaceId": page.get("spaceId"),
                            "childPosition": page.get("childPosition"),
                            "webUrl": page.get("webUrl"),
                        })
                    next_link = data.get("_links", {}).get("next")
                    next_cursor = self._extract_next_cursor(next_link)
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "parentId": page_id,
                        "children": children,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"API request failed: {response.status_code} - {response.text}",
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")