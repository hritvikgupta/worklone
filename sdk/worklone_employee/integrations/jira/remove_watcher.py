from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraRemoveWatcherTool(BaseTool):
    name = "jira_remove_watcher"
    description = "Remove a watcher from a Jira issue"
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
            context_token_keys=("provider_token",),
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
                raise ValueError(f"Failed to fetch accessible resources: {response.status_code} - {response.text}")
            resources = response.json()
            for resource in resources:
                site_url = resource.get("siteUrl", "").rstrip("/")
                if site_url.endswith(domain):
                    return resource["id"]
            raise ValueError(f"No Jira cloud ID found for domain: {domain}")

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
                    "description": "Jira issue key to remove watcher from (e.g., PROJ-123)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Account ID of the user to remove as watcher",
                },
            },
            "required": ["domain", "issueKey", "accountId"],
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
        issue_key = parameters["issueKey"]
        account_id = parameters["accountId"]
        cloud_id = parameters.get("cloudId")
        
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/watchers?accountId={account_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "issueKey": issue_key,
                        "watcherAccountId": account_id,
                        "success": True,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    error_msg = f"Failed to remove watcher from Jira issue ({response.status_code})"
                    try:
                        err = response.json()
                        if err.get("errorMessages"):
                            error_msg = ", ".join(err["errorMessages"])
                        elif err.get("message"):
                            error_msg = err["message"]
                    except Exception:
                        error_msg = response.text or error_msg
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")