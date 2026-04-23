from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListLabelsTool(BaseTool):
    name = "confluence_list_labels"
    description = "List all labels on a Confluence page."
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

    def _extract_next_cursor(self, data: Dict[str, Any]) -> str | None:
        links = data.get("_links", {})
        next_url = links.get("next")
        if next_url:
            parsed_url = urlparse(next_url)
            query_params = parse_qs(parsed_url.query)
            return query_params.get("cursor", [None])[0]
        return data.get("nextPageToken")

    async def _resolve_cloud_id(self, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/userinfo"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            cloud_id = data.get("cloudid")
            if not cloud_id:
                raise ValueError("cloudid not found in userinfo response")
            return cloud_id

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
                    "description": "Confluence page ID to list labels from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of labels to return (default: 25, max: 250)",
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

        try:
            domain = parameters["domain"]
            page_id = parameters["pageId"]
            limit = int(parameters.get("limit", 25))
            cursor = parameters.get("cursor")
            cloud_id = parameters.get("cloudId")
            if not cloud_id:
                cloud_id = await self._resolve_cloud_id(access_token)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid parameters: {str(e)}")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/pages/{page_id}/labels"

        query_params: Dict[str, str] = {"limit": str(limit)}
        if cursor:
            query_params["cursor"] = cursor

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200]:
                    data = response.json()
                    labels = data.get("results", [])
                    next_cursor = self._extract_next_cursor(data)
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {
                        "ts": ts,
                        "labels": labels,
                        "nextCursor": next_cursor,
                    }
                    output_str = json.dumps(output_data)
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")