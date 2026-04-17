from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraDeleteIssueLinkTool(BaseTool):
    name = "jira_delete_issue_link"
    description = "Delete a link between two Jira issues"
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
            context_token_keys=("accessToken",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_jira_cloud_id(self, domain: str, access_token: str) -> str:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources ({resp.status_code}): {resp.text}")
            try:
                resources = resp.json()
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON from accessible resources")
            for resource in resources:
                resource_url = resource.get("url")
                if resource_url == f"https://{domain}":
                    return resource["id"]
            available = [r.get("url", "unknown") for r in resources]
            raise ValueError(f"No cloud ID found for domain '{domain}'. Available sites: {available}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "linkId": {
                    "type": "string",
                    "description": "ID of the issue link to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "linkId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        domain = parameters["domain"]
        link_id = parameters["linkId"]
        cloud_id = parameters.get("cloudId")
        
        try:
            if not cloud_id:
                cloud_id = await self._get_jira_cloud_id(domain, access_token)
            
            url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issueLink/{link_id}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "linkId": link_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    error_msg = f"Failed to delete issue link ({response.status_code}): {response.text}"
                    try:
                        err_data = response.json()
                        if "errorMessages" in err_data:
                            error_msg = ", ".join(err_data["errorMessages"])
                        elif isinstance(err_data, dict) and "message" in err_data:
                            error_msg = err_data["message"]
                        elif isinstance(err_data, list):
                            error_msg = ", ".join(err_data)
                    except json.JSONDecodeError:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")