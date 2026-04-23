from typing import Any, Dict
import httpx
import json
from datetime import datetime
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ConfluenceListPagePropertiesTool(BaseTool):
    name = "confluence_list_page_properties"
    description = "List all custom properties (metadata) attached to a Confluence page."
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

    async def _get_cloud_id(self, domain: str) -> str:
        url = f"https://{domain.strip()}/wiki/rest/api/meta/site"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            site_info = resp.json()
            return site_info["id"]

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
                    "description": "The ID of the page to list properties from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of properties to return (default: 50, max: 250)",
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

        domain = parameters["domain"]
        page_id = parameters["pageId"]
        limit = int(parameters.get("limit", 50))
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId")

        try:
            if not cloud_id:
                cloud_id = await self._get_cloud_id(domain)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to resolve cloudId: {str(e)}")

        base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages/{page_id}/properties"
        query: Dict[str, Any] = {
            "limit": limit,
            "expand": "version",
        }
        if cursor:
            query["cursor"] = cursor
        url = base_url + ("?" + urlencode(query) if query else "")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    properties = []
                    for p in data.get("results", []):
                        prop = {
                            "id": p["id"],
                            "key": p["key"],
                            "value": p["value"],
                            "version": p.get("version"),
                        }
                        properties.append(prop)
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "pageId": page_id,
                        "properties": properties,
                        "nextCursor": data.get("next"),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")