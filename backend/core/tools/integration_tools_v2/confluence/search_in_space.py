from typing import Any, Dict
import httpx
import json
import urllib.parse
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceSearchInSpaceTool(BaseTool):
    name = "confluence_search_in_space"
    description = "Search for content within a specific Confluence space. Optionally filter by text query and content type."
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

    def _escape_cql_value(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    async def _get_confluence_cloud_id(self, domain: str, access_token: str) -> str:
        ar_url = "https://api.atlassian.com/oauth/token/accessible-resources"
        ar_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            ar_resp = await client.get(ar_url, headers=ar_headers)
            if ar_resp.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources: {ar_resp.text}")
            resources = ar_resp.json()
            wiki_url = f"https://{domain}/wiki"
            for resource in resources:
                if resource.get("url") == wiki_url:
                    return resource["id"]
            raise ValueError(f"No Confluence cloud ID found for domain {domain}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "spaceKey": {
                    "type": "string",
                    "description": "The key of the Confluence space to search in (e.g., \"ENG\", \"HR\")",
                },
                "query": {
                    "type": "string",
                    "description": "Text search query. If not provided, returns all content in the space.",
                },
                "contentType": {
                    "type": "string",
                    "description": "Filter by content type: page, blogpost, attachment, or comment",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 25, max: 250)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters.get("domain")
        if not domain:
            return ToolResult(success=False, output="", error="Domain is required")
        
        space_key_raw = parameters.get("spaceKey")
        if not space_key_raw:
            return ToolResult(success=False, output="", error="Space key is required")
        space_key = space_key_raw.strip()
        
        cloud_id = parameters.get("cloudId")
        if not cloud_id:
            cloud_id = await self._get_confluence_cloud_id(domain, access_token)
        
        cql = f'space = "{self._escape_cql_value(space_key)}"'
        
        query = parameters.get("query")
        if query:
            cql += f' AND text ~ "{self._escape_cql_value(query)}"'
        
        content_type = parameters.get("contentType")
        if content_type:
            cql += f' AND type = "{self._escape_cql_value(content_type)}"'
        
        limit_val = parameters.get("limit", 25)
        try:
            limit = max(1, min(int(limit_val), 250))
        except (ValueError, TypeError):
            limit = 25
        
        search_params = urllib.parse.urlencode({"cql": cql, "limit": str(limit)})
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/search?{search_params}"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for result in data.get("results", []):
                        content = result.get("content", {})
                        results.append({
                            "id": content.get("id") or result.get("id"),
                            "title": content.get("title") or result.get("title"),
                            "type": content.get("type") or result.get("type"),
                            "status": content.get("status"),
                            "url": result.get("url") or result.get("_links", {}).get("webui", ""),
                            "excerpt": result.get("excerpt", ""),
                            "lastModified": result.get("lastModified"),
                        })
                    processed = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "spaceKey": space_key,
                        "totalSize": data.get("totalSize", len(results)),
                        "results": results,
                    }
                    return ToolResult(success=True, output=json.dumps(processed), data=processed)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"Failed to search in space ({response.status_code})")
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")