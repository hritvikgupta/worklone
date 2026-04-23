from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeletePagePropertyTool(BaseTool):
    name = "confluence_delete_page_property"
    description = "Delete a content property from a Confluence page by its property ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="Access token for Confluence",
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
                    "description": "The ID of the page containing the property",
                },
                "propertyId": {
                    "type": "string",
                    "description": "The ID of the property to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId", "propertyId"],
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
        property_id = parameters["propertyId"].strip()
        cloud_id = parameters.get("cloudId", "").strip()

        url = f"https://{domain}/wiki/rest/api/content/{page_id}/property/{property_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code == 204:
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {
                        "ts": ts,
                        "pageId": page_id,
                        "propertyId": property_id,
                        "deleted": True,
                    }
                    return ToolResult(success=True, output="", data=output_data)
                elif response.status_code in [200, 201]:
                    data = response.json() if response.content else {}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")