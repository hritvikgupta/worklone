from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraUpdateCommentTool(BaseTool):
    name = "jira_update_comment"
    description = "Update an existing comment on a Jira issue"
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
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            resources = response.json()
            for resource in resources:
                resource_url = resource.get("url", "")
                if resource_url.rstrip("/").endswith(domain):
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
                "issueKey": {
                    "type": "string",
                    "description": "Jira issue key containing the comment (e.g., PROJ-123)",
                },
                "commentId": {
                    "type": "string",
                    "description": "ID of the comment to update",
                },
                "body": {
                    "type": "string",
                    "description": "Updated comment text",
                },
                "visibility": {
                    "type": "object",
                    "description": 'Restrict comment visibility. Object with "type" ("role" or "group") and "value" (role/group name).',
                },
            },
            "required": ["domain", "issueKey", "commentId", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        try:
            domain = parameters["domain"]
            issue_key = parameters["issueKey"]
            comment_id = parameters["commentId"]
            body_text = parameters["body"]
            visibility = parameters.get("visibility")
            cloud_id = parameters.get("cloudId")
            
            if not cloud_id:
                cloud_id = await self._get_cloud_id(domain, access_token)
            
            url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment/{comment_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": body_text,
                                }
                            ],
                        }
                    ],
                }
            }
            if visibility:
                payload["visibility"] = visibility
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msgs = err_data.get("errorMessages", [])
                        if error_msgs:
                            error_msg = ", ".join(error_msgs)
                        elif "message" in err_data:
                            error_msg = err_data["message"]
                    except Exception:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to update comment ({response.status_code}): {error_msg}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")