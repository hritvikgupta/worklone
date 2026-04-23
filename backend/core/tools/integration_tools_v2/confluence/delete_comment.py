from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeleteCommentTool(BaseTool):
    name = "confluence_delete_comment"
    description = "Delete a comment from a Confluence page."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "commentId": {
                    "type": "string",
                    "description": "Confluence comment ID to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "commentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain: str = parameters["domain"]
        comment_id: str = parameters["commentId"]
        cloud_id: str | None = parameters.get("cloudId")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            if cloud_id is None:
                accessible_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                acc_headers = headers.copy()
                acc_response = await client.get(accessible_url, headers=acc_headers)
                if acc_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch accessible resources: {acc_response.text}",
                    )
                resources: list[Dict[str, Any]] = acc_response.json()
                cloud_id = None
                for resource in resources:
                    site_url: str = resource.get("siteUrl", "")
                    if site_url.startswith(f"https://{domain}/"):
                        cloud_id = resource["id"]
                        break
                if cloud_id is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"No Confluence cloud ID found for domain '{domain}'",
                    )

            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/content/{comment_id}"

            try:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 204]:
                    ts = datetime.now(timezone.utc).isoformat()
                    data = {
                        "ts": ts,
                        "commentId": comment_id,
                        "deleted": True,
                    }
                    return ToolResult(
                        success=True,
                        output=response.text or "Comment deleted successfully.",
                        data=data,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to delete comment. Status: {response.status_code}, Body: {response.text}",
                    )
            except Exception as e:
                return ToolResult(success=False, output="", error=f"API error: {str(e)}")