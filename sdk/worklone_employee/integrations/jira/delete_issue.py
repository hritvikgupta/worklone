from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraDeleteIssueTool(BaseTool):
    name = "jira_delete_issue"
    description = "Delete a Jira issue"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="Access token for Jira",
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

    async def _get_jira_cloud_id(self, access_token: str, domain: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                resources = response.json()
                for resource in resources:
                    resource_url = resource.get("url", "")
                    if resource_url.endswith(domain):
                        return resource["id"]
                available = [r.get("url", "unknown") for r in resources]
                raise ValueError(f"No accessible resource found matching domain '{domain}'. Available: {available}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch accessible resources: {e.response.status_code} - {e.response.text[:200]}")
        except Exception as e:
            raise ValueError(f"Failed to fetch Jira Cloud ID: {str(e)}")

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
                    "description": "Jira issue key to delete (e.g., PROJ-123)",
                },
                "deleteSubtasks": {
                    "type": "boolean",
                    "description": "Whether to delete subtasks. If false, parent issues with subtasks cannot be deleted.",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        issue_key: str = parameters["issueKey"]
        delete_subtasks: bool = parameters.get("deleteSubtasks", False)
        cloud_id: str | None = parameters.get("cloudId")
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        if not cloud_id:
            cloud_id = await self._get_jira_cloud_id(access_token, domain)
        
        delete_subtasks_param = "?deleteSubtasks=true" if delete_subtasks else ""
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}{delete_subtasks_param}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
            
            if response.status_code == 204:
                result = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "issueKey": issue_key,
                    "success": True,
                }
                return ToolResult(success=True, output=json.dumps(result), data=result)
            else:
                error_msg = f"Failed to delete Jira issue ({response.status_code})"
                content_type = response.headers.get("content-type", "").lower()
                try:
                    if "application/json" in content_type:
                        err_data = response.json()
                        if isinstance(err_data, dict):
                            error_messages = err_data.get("errorMessages", [])
                            if error_messages:
                                error_msg = ", ".join(error_messages)
                            elif err_data.get("message"):
                                error_msg = err_data["message"]
                    else:
                        text = response.text[:200]
                        error_msg += f" - Received HTML/text response. Check authentication and permissions. Response: {text}"
                except Exception:
                    pass
                return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")