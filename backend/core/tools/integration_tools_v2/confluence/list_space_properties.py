from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListSpacePropertiesTool(BaseTool):
    name = "confluence_list_space_properties"
    description = "List properties on a Confluence space."
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
                "spaceId": {
                    "type": "string",
                    "description": "Space ID to list properties for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of properties to return (default: 50, max: 250)",
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
            "required": ["domain", "spaceId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = parameters["domain"].strip()
        space_id = parameters["spaceId"]
        limit = int(parameters.get("limit", 50))
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId", "").strip()

        if not cloud_id:
            resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
            headers_auth = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp_resources = await client.get(resources_url, headers=headers_auth)
                    if resp_resources.status_code != 200:
                        return ToolResult(
                            success=False, output="", error=f"Failed to fetch accessible resources: {resp_resources.text}"
                        )
                    resources = resp_resources.json()
                    expected_url = f"https://{domain}.atlassian.net"
                    matching_cloud_id = None
                    for resource in resources:
                        resource_url = resource.get("url", "").rstrip("/")
                        if resource_url == expected_url:
                            matching_cloud_id = resource["id"]
                            break
                    if not matching_cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"No accessible Confluence cloud found for domain '{domain}'",
                        )
                    cloud_id = matching_cloud_id
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Error fetching cloud ID: {str(e)}")

        api_base = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api"
        url = f"{api_base}/space/{space_id}/property"

        query_params = {}
        if limit:
            query_params["limit"] = limit
        if cursor:
            query_params["cursor"] = cursor

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200]:
                    data = response.json()
                    properties = [
                        {
                            "id": item["id"],
                            "key": item["key"],
                            "value": item["value"],
                        }
                        for item in data.get("results", [])
                    ]
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "properties": properties,
                        "spaceId": space_id,
                        "nextCursor": data.get("nextCursor"),
                    }
                    return ToolResult(
                        success=True, output=json.dumps(output_data), data=output_data
                    )
                else:
                    return ToolResult(
                        success=False, output="", error=f"API error {response.status_code}: {response.text}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")