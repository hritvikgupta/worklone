from typing import Any, Dict
import httpx
import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeleteSpacePropertyTool(BaseTool):
    name = "confluence_delete_space_property"
    description = "Delete a property from a Confluence space."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="Confluence OAuth access token",
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
                "spaceId": {
                    "type": "string",
                    "description": "Space ID the property belongs to",
                },
                "propertyId": {
                    "type": "string",
                    "description": "Property ID to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceId", "propertyId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        domain: str = parameters["domain"]
        space_id: str = parameters["spaceId"]
        property_id: str = parameters["propertyId"]
        cloud_id: str | None = parameters.get("cloudId")

        if cloud_id:
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/spaces/{space_id}/properties/{property_id}"
        else:
            url = f"https://{domain}/wiki/rest/api/space/{space_id}/property/{property_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    output_data = {
                        "ts": ts,
                        "spaceId": space_id,
                        "propertyId": property_id,
                        "deleted": True,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")