from typing import Any, Dict
import httpx
import json
import urllib.parse
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListSpacesTool(BaseTool):
    name = "confluence_list_spaces"
    description = "List all Confluence spaces accessible to the user."
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
                "limit": {
                    "type": "number",
                    "description": "Maximum number of spaces to return (default: 25, max: 250)",
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
            "required": ["domain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        if "domain" not in parameters:
            return ToolResult(success=False, output="", error="Domain is required.")
        
        domain = parameters["domain"].strip()
        if not domain:
            return ToolResult(success=False, output="", error="Invalid domain.")
        
        try:
            limit = int(parameters.get("limit", 25))
        except (ValueError, TypeError):
            limit = 25
        
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        if not cloud_id:
            instance_url = f"https://{domain}/wiki/rest/api/instance"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(instance_url, headers=headers)
                    if resp.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to fetch cloud ID: {resp.status_code} - {resp.text}"
                        )
                    instance_data = resp.json()
                    cloud_id = instance_data.get("id")
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error="Cloud ID not found in instance information."
                        )
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Error fetching cloud ID: {str(e)}")
        
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/spaces"
        
        query_params: dict[str, Any] = {"limit": limit}
        if cursor:
            query_params["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers, params=query_params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    spaces = data.get("results", [])
                    next_cursor = None
                    links = data.get("_links", {})
                    if "next" in links:
                        next_url = links["next"]
                        parsed = urllib.parse.urlparse(next_url)
                        query_dict = urllib.parse.parse_qs(parsed.query)
                        next_cursor = query_dict.get("cursor", [None])[0]
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "spaces": spaces,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"API error: {resp.status_code} - {resp.text}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")