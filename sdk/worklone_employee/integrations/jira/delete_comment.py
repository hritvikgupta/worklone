from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraDeleteCommentTool(BaseTool):
    name = "jira_delete_comment"
    description = "Delete a comment from a Jira issue"
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
            context_token_keys=("jira_token",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise ValueError(f"Failed to fetch accessible resources: {response.status_code} - {response.text}")
                resources = response.json()
                domain_lower = domain.lower()
                for resource in resources:
                    resource_url = resource.get("url", "").lower()
                    if domain_lower in resource_url:
                        return resource["id"]
                raise ValueError(f"No matching cloud ID found for domain '{domain}'")
        except Exception as e:
            raise ValueError(f"Error fetching cloud ID: {str(e)}")

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
                    "description": "Jira issue key containing the comment (e.g., PROJ-123)",
                },
                "commentId": {
                    "type": "string",
                    "description": "ID of the comment to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey", "commentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        issue_key = parameters["issueKey"]
        comment_id = parameters["commentId"]
        cloud_id = parameters.get("cloudId")
        
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment/{comment_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "issueKey": issue_key,
                        "commentId": comment_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msgs = err_data.get("errorMessages", [])
                        if error_msgs:
                            error_msg = ", ".join(error_msgs)
                        elif "message" in err_data:
                            error_msg = err_data["message"]
                    except:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to delete comment from Jira issue ({response.status_code}): {error_msg}"
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")