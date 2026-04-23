from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceSearchTool(BaseTool):
    name = "confluence_search"
    description = "Search for content across Confluence pages, blog posts, and other content."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    @staticmethod
    def _escape_cql_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

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
            context_token_keys=("accessToken",},
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",},
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_confluence_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError("Failed to fetch accessible resources")
            data = response.json()
            for resource in data:
                resource_url = resource.get("url", "")
                if resource_url == f"https://{domain}/wiki":
                    return resource["id"]
            raise ValueError(f"Could not find Confluence cloud ID for domain '{domain}'. Ensure the access token has access to the site.")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 25)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters.get("domain")
        if not domain:
            return ToolResult(success=False, output="", error="Domain is required.")
        
        query = parameters.get("query")
        if not query:
            return ToolResult(success=False, output="", error="Search query is required.")
        
        limit = int(parameters.get("limit", 25))
        
        cloud_id = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            if cloud_id is None:
                cloud_id = await self._get_confluence_cloud_id(domain, access_token)
            
            cql = f'text ~ "{self._escape_cql_value(query)}"'
            search_params_str = urlencode({"cql": cql, "limit": str(limit)})
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/search?{search_params_str}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for result in data.get("results", []):
                        space_data = result.get("resultGlobalContainer") or result.get("content", {}).get("space")
                        item = {
                            "id": result.get("content", {}).get("id") or result.get("id"),
                            "title": result.get("content", {}).get("title") or result.get("title"),
                            "type": result.get("content", {}).get("type") or result.get("type"),
                            "url": result.get("url") or result.get("_links", {}).get("webui", ""),
                            "excerpt": result.get("excerpt", ""),
                            "status": result.get("content", {}).get("status"),
                            "spaceKey": result.get("resultGlobalContainer", {}).get("key") or result.get("content", {}).get("space", {}).get("key"),
                            "space": None,
                            "lastModified": result.get("lastModified") or result.get("content", {}).get("history", {}).get("lastUpdated", {}).get("when"),
                            "entityType": result.get("entityType"),
                        }
                        if space_data:
                            item["space"] = {
                                "id": space_data.get("id"),
                                "key": space_data.get("key"),
                                "name": space_data.get("name") or space_data.get("title"),
                            }
                        results.append(item)
                    
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {"ts": ts, "results": results}
                    output = json.dumps(output_data)
                    return ToolResult(success=True, output=output, data=output_data)
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("message", f"Failed to search Confluence ({response.status_code})")
                    return ToolResult(success=False, output="", error=error_message)
                    
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")