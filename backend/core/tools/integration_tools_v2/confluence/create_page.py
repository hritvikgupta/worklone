from typing import Dict, Any
import httpx
import uuid
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceCreatePageTool(BaseTool):
    name = "confluence_create_page"
    description = "Create a new page in a Confluence space."
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

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/ex/confluence/api/v1/teams"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch teams: {response.status_code} - {response.text}")
            teams: list[dict[str, Any]] = response.json()
            normalized_domain = domain.lstrip("www.").lower()
            for team in teams:
                team_url = team.get("url", "")
                if isinstance(team_url, str):
                    team_host = httpx.URL(team_url).host.lstrip("www.").lower()
                    if team_host == normalized_domain:
                        return team["id"]
            raise ValueError(f"No matching cloud ID found for domain '{domain}'")

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
                    "description": "Confluence space ID where the page will be created",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the new page",
                },
                "content": {
                    "type": "string",
                    "description": "Page content in Confluence storage format (HTML)",
                },
                "parentId": {
                    "type": "string",
                    "description": "Parent page ID if creating a child page",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceId", "title", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain: str = parameters["domain"]
        space_id: str = parameters["spaceId"]
        title: str = parameters["title"]
        content: str = parameters["content"]
        parent_id: str | None = parameters.get("parentId")
        cloud_id: str | None = parameters.get("cloudId")

        if not space_id.isdigit():
            return ToolResult(
                success=False,
                output="",
                error="Invalid Space ID. The Space ID must be a numeric value, not the space key from the URL. Use the \"list\" operation to get all spaces with their numeric IDs.",
            )

        if cloud_id:
            try:
                uuid.UUID(cloud_id)
            except ValueError:
                return ToolResult(
                    success=False,
                    output="",
                    error="Invalid Cloud ID format. Must be a valid UUID.",
                )

        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": content,
            },
        }
        if parent_id and parent_id.strip():
            body["parentId"] = parent_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_data = None
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    error_msg = f"Failed to create Confluence page ({response.status_code})"
                    if isinstance(error_data, dict):
                        if msg := error_data.get("message"):
                            error_msg = msg
                        elif errors := error_data.get("errors"):
                            if isinstance(errors, list) and errors:
                                first_error = errors[0]
                                if isinstance(first_error, dict) and (title := first_error.get("title")):
                                    if "'spaceId'" in title and "Long" in title:
                                        error_msg = "Invalid Space ID. Use the list spaces operation to find valid space IDs."
                                    else:
                                        error_msg = title
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")