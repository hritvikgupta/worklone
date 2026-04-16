from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraDeleteWorklogTool(BaseTool):
    name = "jira_delete_worklog"
    description = "Delete a worklog entry from a Jira issue"
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

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources ({response.status_code}): {response.text}")
            resources = response.json()
            for resource in resources:
                resource_url = resource.get("url", "").rstrip("/")
                if resource_url == f"https://{domain}":
                    return resource["id"]
            raise ValueError(f"No cloud ID found for domain '{domain}'")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "issueKey": {
                    "type": "string",
                    "description": "Jira issue key containing the worklog (e.g., PROJ-123)",
                },
                "worklogId": {
                    "type": "string",
                    "description": "ID of the worklog entry to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey", "worklogId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        issue_key = parameters["issueKey"]
        worklog_id = parameters["worklogId"]
        cloud_id = parameters.get("cloudId")
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/worklog/{worklog_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    output = {
                        "ts": datetime.utcnow().isoformat(),
                        "issueKey": issue_key,
                        "worklogId": worklog_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output), data=output)
                else:
                    error_msg = f"Failed to delete worklog from Jira issue ({response.status_code})"
                    try:
                        err = response.json()
                        if isinstance(err, dict):
                            if "errorMessages" in err:
                                error_msg = ", ".join(err["errorMessages"])
                            elif "message" in err:
                                error_msg = err["message"]
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")