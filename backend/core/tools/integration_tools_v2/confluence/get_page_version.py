from typing import Any, Dict
import httpx
import base64
import re
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetPageVersionTool(BaseTool):
    name = "confluence_get_page_version"
    description = "Get details about a specific version of a Confluence page."
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

    def _strip_html(self, html: str) -> str:
        return re.sub(r'<[^>]+>', '', html or '')

    async def _get_cloud_id(self, access_token: str, domain: str, client: httpx.AsyncClient) -> str:
        token_info_url = "https://api.atlassian.com/oauth/token/info"
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get(token_info_url, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Failed to fetch token info: {resp.status_code} {resp.text}")
        data = resp.json()
        sites = data.get("sites", [])
        for site in sites:
            site_url = site.get("url", "")
            if f"{domain}.atlassian.net" in site_url:
                return site["cloudId"]
        raise ValueError(f"No cloudId found for domain '{domain}'")

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
                    "description": "The ID of the page",
                },
                "versionNumber": {
                    "type": "number",
                    "description": "The version number to retrieve (e.g., 1, 2, 3)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId", "versionNumber"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        page_id = parameters["pageId"].strip()
        version_number = int(parameters["versionNumber"])
        cloud_id = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if not cloud_id:
                    cloud_id = await self._get_cloud_id(access_token, domain, client)
                
                base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2"
                
                # Fetch version details
                version_url = f"{base_url}/pages/{page_id}/version/{version_number}"
                version_resp = await client.get(version_url, headers=headers)
                if not 200 <= version_resp.status_code < 300:
                    return ToolResult(success=False, output="", error=f"Version API error {version_resp.status_code}: {version_resp.text}")
                version_data = version_resp.json()
                
                # Fetch body storage
                body_url = f"{base_url}/pages/{page_id}/body?version={version_number}&body-format=storage"
                body_resp = await client.get(body_url, headers=headers)
                if not 200 <= body_resp.status_code < 300:
                    return ToolResult(success=False, output="", error=f"Body storage API error {body_resp.status_code}: {body_resp.text}")
                body_data = body_resp.json()
                
                # Fetch body view for stripped content
                view_url = f"{base_url}/pages/{page_id}/body?version={version_number}&body-format=view"
                view_resp = await client.get(view_url, headers=headers)
                if not 200 <= view_resp.status_code < 300:
                    return ToolResult(success=False, output="", error=f"Body view API error {view_resp.status_code}: {view_resp.text}")
                view_data = view_resp.json()
                
                content = self._strip_html(view_data.get("value", ""))
                
                version = {
                    "number": version_data.get("versionNumber"),
                    "message": version_data.get("message"),
                    "minorEdit": version_data.get("minorEdit"),
                    "authorId": version_data.get("author", {}).get("accountId"),
                    "createdAt": version_data.get("createdAt"),
                    "contentTypeModified": version_data.get("contentTypeModified"),
                    "collaborators": None,
                    "prevVersion": version_data.get("previousVersion", {}).get("number"),
                    "nextVersion": version_data.get("nextVersion", {}).get("number"),
                }
                
                body = None
                if body_data.get("value"):
                    body = {
                        "storage": {
                            "value": body_data.get("value"),
                            "representation": body_data.get("representation"),
                        }
                    }
                
                output_data = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "pageId": page_id,
                    "title": version_data.get("title"),
                    "content": content,
                    "version": version,
                    "body": body,
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data
                )
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")