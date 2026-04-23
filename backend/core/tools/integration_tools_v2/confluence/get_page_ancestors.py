from typing import Any, Dict
import httpx
import json
import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ConfluenceGetPageAncestorsTool(BaseTool):
    name = "confluence_get_page_ancestors"
    description = "Get the ancestor (parent) pages of a specific Confluence page. Returns the full hierarchy from the page up to the root."
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
                    "description": "The ID of the page to get ancestors for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of ancestors to return (default: 25, max: 250)",
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
        
        domain = parameters["domain"].strip()
        page_id = parameters["pageId"].strip()
        limit = parameters.get("limit", 25)
        limit = min(int(limit), 250)
        
        url = f"https://{domain}.atlassian.net/wiki/rest/api/content/{page_id}/ancestor?limit={limit}&expand=ancestors.space"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    api_data = response.json()
                    ancestors = []
                    for anc in api_data.get("ancestors", []):
                        space_id = anc.get("space", {}).get("id") if anc.get("space") else None
                        web_ui = anc.get("_links", {}).get("webui")
                        web_url = f"https://{domain}.atlassian.net{web_ui}" if web_ui else None
                        ancestors.append({
                            "id": anc.get("id"),
                            "title": anc.get("title"),
                            "status": anc.get("status"),
                            "spaceId": space_id,
                            "webUrl": web_url,
                        })
                    output_data = {
                        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "pageId": page_id,
                        "ancestors": ancestors,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")