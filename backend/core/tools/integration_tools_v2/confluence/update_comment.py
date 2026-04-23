from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceUpdateCommentTool(BaseTool):
    name = "confluence_update_comment"
    description = "Update an existing comment on a Confluence page."
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
            context_token_keys=("confluence_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        space_url = f"https://{domain}/wiki/rest/api/space?limit=1"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(space_url, headers=headers)
            if resp.status_code == 200:
                cloud_id = resp.headers.get("Atlassian-Cloud-ID")
                if cloud_id:
                    return cloud_id
            raise ValueError(f"Failed to fetch cloudId. Status: {resp.status_code}, Response: {resp.text}")

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
                    "description": "Confluence comment ID to update",
                },
                "comment": {
                    "type": "string",
                    "description": "Updated comment text in Confluence storage format",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "commentId", "comment"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        try:
            domain = parameters["domain"]
            comment_id = parameters["commentId"]
            comment = parameters["comment"]
            cloud_id = parameters.get("cloudId")
            if cloud_id is None:
                cloud_id = await self._get_cloud_id(access_token, domain)

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2"
            get_url = f"{base_url}/comments/{comment_id}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp_get = await client.get(get_url, headers=headers)
                if resp_get.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch comment: {resp_get.status_code} - {resp_get.text}",
                    )
                comment_data = resp_get.json()
                version_num = comment_data["version"]["number"] + 1

                update_payload = {
                    "version": {"number": version_num},
                    "body": {
                        "representation": "storage",
                        "value": comment,
                    },
                }

                resp_update = await client.put(get_url, headers=headers, json=update_payload)
                if resp_update.status_code in [200, 201, 204]:
                    updated_data = resp_update.json() if resp_update.content else {}
                    ts = datetime.now(timezone.utc).isoformat()
                    output_data = {
                        "ts": ts,
                        "commentId": updated_data.get("id") or comment_id,
                        "updated": True,
                    }
                    return ToolResult(
                        success=True,
                        output=str(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to update comment: {resp_update.status_code} - {resp_update.text}",
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")