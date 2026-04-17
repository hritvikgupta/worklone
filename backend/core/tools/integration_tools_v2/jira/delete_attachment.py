from typing import Any, Dict, Optional
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraDeleteAttachmentTool(BaseTool):
    name = "jira_delete_attachment"
    description = "Delete an attachment from a Jira issue"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="OAuth access token for Jira",
                env_var="JIRA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "jira",
            context=context,
            context_token_keys=("access_token", "provider_token"),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_jira_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to get accessible resources: {response.status_code} - {response.text}")
            resources = response.json()
            expected_url = f"https://{domain.rstrip('/')}"
            for resource in resources:
                resource_url = resource.get("url", "").rstrip("/")
                if resource_url == expected_url:
                    return resource["id"]
            raise ValueError(f"No matching cloud ID found for domain '{domain}'")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "attachmentId": {
                    "type": "string",
                    "description": "ID of the attachment to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "attachmentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        attachment_id = parameters["attachmentId"]
        cloud_id: Optional[str] = parameters.get("cloudId")
        
        if not cloud_id:
            cloud_id = await self._get_jira_cloud_id(domain, access_token)
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/attachment/{attachment_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "attachmentId": attachment_id,
                        "success": True,
                    }
                    output_str = json.dumps(output_data)
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_messages = err_data.get("errorMessages", [])
                        if error_messages:
                            error_msg = ", ".join(error_messages)
                        elif err_data.get("message"):
                            error_msg = err_data["message"]
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to delete attachment from Jira issue ({response.status_code}): {error_msg}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")