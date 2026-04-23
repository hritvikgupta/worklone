from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListPageVersionsTool(BaseTool):
    name = "confluence_list_page_versions"
    description = "List all versions (revision history) of a Confluence page."
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
            context_token_keys=("accessToken", "provider_token"),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, access_token: str, domain: str) -> str | None:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        teams_url = "https://api.atlassian.com/ex/confluence/api/v2/teams"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(teams_url, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                teams = data.get("results", [])
                for team in teams:
                    team_url = team.get("url", "")
                    if team_url.startswith("https://"):
                        parsed_domain = team_url.split("/")[2]
                        if parsed_domain == domain:
                            return team["id"]
                return None
        except Exception:
            return None

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
                    "description": "The ID of the page to get versions for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of versions to return (default: 50, max: 250)",
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
        
        domain = parameters.get("domain")
        page_id = parameters.get("pageId")
        limit = parameters.get("limit", 50)
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId")
        
        if not domain or not page_id:
            return ToolResult(success=False, output="", error="Missing required parameters: domain and pageId.")
        
        if not cloud_id:
            cloud_id = await self._get_cloud_id(access_token, domain.strip())
            if not cloud_id:
                return ToolResult(success=False, output="", error="Could not find Confluence cloud ID for the given domain.")
        
        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/pages/{page_id.strip()}/versions"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        params_dict: dict[str, Any] = {}
        if limit is not None:
            params_dict["limit"] = int(limit)
        if cursor:
            params_dict["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")