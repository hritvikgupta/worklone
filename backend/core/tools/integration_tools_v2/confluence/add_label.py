from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceAddLabelTool(BaseTool):
    name = "confluence_add_label"
    description = "Add a label to a Confluence page for organization and categorization."
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
            context_token_keys=("access_token",},
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",},
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
                    "description": "Confluence page ID to add the label to",
                },
                "labelName": {
                    "type": "string",
                    "description": "Name of the label to add",
                },
                "prefix": {
                    "type": "string",
                    "description": "Label prefix: global (default), my, team, or system",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId", "labelName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = (parameters.get("domain") or "").strip()
        page_id = (parameters.get("pageId") or "").strip()
        label_name = (parameters.get("labelName") or "").strip()
        prefix = (parameters.get("prefix") or "global").strip()
        cloud_id = (parameters.get("cloudId") or "").strip()

        if not domain or not page_id or not label_name:
            return ToolResult(success=False, output="", error="Domain, pageId, and labelName are required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if not cloud_id:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        "https://api.atlassian.com/oauth/token/accessible-resources",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to fetch accessible resources: {resp.status_code} {resp.text}",
                        )
                    resources: list[Dict[str, Any]] = resp.json()
                    for resource in resources:
                        resource_url = resource.get("url", "")
                        if resource_url == f"https://{domain}":
                            cloud_id = resource["id"]
                            break
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"No cloud ID found for domain '{domain}'",
                        )
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Error fetching cloud ID: {str(e)}")

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/content/{page_id}/label/default"

        body = {
            "name": label_name,
            "prefix": prefix,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=f"API error {response.status_code}: {response.text}")

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")