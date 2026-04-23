from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceCreateSpaceTool(BaseTool):
    name = "confluence_create_space"
    description = "Create a new Confluence space."
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
            ),
            CredentialRequirement(
                key="domain",
                description="Your Confluence domain (e.g., yourcompany.atlassian.net)",
                env_var="CONFLUENCE_DOMAIN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="cloudId",
                description="Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                env_var="CONFLUENCE_CLOUD_ID",
                required=False,
                auth_type="api_key",
            ),
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("provider_token",},
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",},
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                sites = response.json()
                expected_url = f"https://{domain}"
                for site in sites:
                    site_url = site.get("url", "").rstrip("/")
                    if site_url == expected_url:
                        return site["id"]
                raise ValueError(f"No accessible Confluence site found for domain '{domain}'.")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch accessible resources: HTTP {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Error fetching cloud ID: {str(e)}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new space",
                },
                "key": {
                    "type": "string",
                    "description": "Unique key for the space (uppercase, no spaces)",
                },
                "description": {
                    "type": "string",
                    "description": "Description for the new space",
                },
            },
            "required": ["name", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = context.get("domain") if context else None
        if not domain:
            return ToolResult(success=False, output="", error="Confluence domain not configured.")

        cloud_id = context.get("cloudId") if context else None
        try:
            if cloud_id is None:
                cloud_id = await self._get_cloud_id(access_token, domain)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/spaces"

        body = {
            "name": parameters["name"],
            "key": parameters["key"],
        }
        description = parameters.get("description")
        if description:
            body["description"] = {
                "plain": {
                    "value": description,
                },
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")