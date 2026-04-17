from typing import Any, Dict
import httpx
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraAddWatcherTool(BaseTool):
    name = "jira_add_watcher"
    description = "Add a watcher to a Jira issue to receive notifications about updates"
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
                    "description": "Jira issue key to add watcher to (e.g., PROJ-123)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Account ID of the user to add as watcher",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey", "accountId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers_base = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        domain = parameters["domain"].strip().rstrip("/")
        issue_key = parameters["issueKey"]
        account_id = parameters["accountId"]
        cloud_id = parameters.get("cloudId")
        
        if not cloud_id:
            resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(resources_url, headers=headers_base)
                    
                    if resp.status_code != 200:
                        error_msg = resp.text
                        try:
                            err_data = resp.json()
                            error_msg = ", ".join(err_data.get("errorMessages", [])) or err_data.get("message", error_msg)
                        except Exception:
                            pass
                        return ToolResult(success=False, output="", error=f"Failed to fetch accessible resources ({resp.status_code}): {error_msg}")
                    
                    resources: list[dict[str, Any]] = resp.json()
                    
                    cloud_id = None
                    for resource in resources:
                        resource_url = resource.get("url", "").strip().rstrip("/")
                        if "://" in resource_url:
                            parsed_domain = resource_url.split("://", 1)[1].rstrip("/")
                        else:
                            parsed_domain = resource_url.rstrip("/")
                        if parsed_domain == domain:
                            cloud_id = resource["id"]
                            break
                    
                    if not cloud_id:
                        return ToolResult(success=False, output="", error=f"No matching cloud ID found for domain '{domain}'")
                        
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Error fetching cloud ID: {str(e)}")
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/watchers"
        headers = {
            **headers_base,
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=account_id)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "issueKey": issue_key,
                        "watcherAccountId": account_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    error_msg = response.text
                    try:
                        err = response.json()
                        if isinstance(err, dict):
                            error_msg = ", ".join(err.get("errorMessages", [])) or err.get("message", error_msg)
                        elif isinstance(err, list):
                            error_msg = ", ".join(str(e) for e in err)
                    except Exception:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to add watcher to Jira issue ({response.status_code}): {error_msg}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")