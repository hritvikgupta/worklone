from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraAddCommentTool(BaseTool):
    name = "jira_add_comment"
    description = "Add a comment to a Jira issue"
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

    def _extract_adf_text(self, adf: Any) -> str:
        if not isinstance(adf, dict):
            return ""
        node_type = adf.get("type")
        if node_type == "text":
            return adf.get("text", "")
        text = ""
        content = adf.get("content", [])
        if isinstance(content, list):
            for child in content:
                text += self._extract_adf_text(child)
        return text

    def _transform_user(self, author: Any) -> Dict[str, str]:
        if not author:
            return {"accountId": "", "displayName": ""}
        return {
            "accountId": author.get("accountId", ""),
            "displayName": author.get("displayName", ""),
        }

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to get accessible resources: {response.status_code} - {response.text}")
            sites = response.json()
            for site in sites:
                site_url = site.get("url", "").rstrip("/")
                if site_url == f"https://{domain}":
                    return site["id"]
            raise Exception(f"No cloud ID found for domain '{domain}'")

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
                    "description": "Jira issue key to add comment to (e.g., PROJ-123)",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body text",
                },
                "visibility": {
                    "type": "object",
                    "description": 'Restrict comment visibility. Object with "type" ("role" or "group") and "value" (role/group name).',
                },
            },
            "required": ["domain", "issueKey", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        issue_key = parameters["issueKey"]
        body_text = parameters["body"]
        visibility = parameters.get("visibility")
        cloud_id = parameters.get("cloudId")
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        payload: Dict[str, Any] = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body_text}],
                    },
                ],
            },
        }
        if visibility:
            payload["visibility"] = visibility
        
        try:
            if cloud_id:
                url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment"
            else:
                cloud_id = await self._get_cloud_id(domain, access_token)
                url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    transformed = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "issueKey": issue_key,
                        "commentId": data.get("id", "unknown"),
                        "body": self._extract_adf_text(data.get("body")) or body_text,
                        "author": self._transform_user(data.get("author")),
                        "created": data.get("created", ""),
                        "updated": data.get("updated", ""),
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                else:
                    error_msg = response.text
                    try:
                        err = response.json()
                        error_msgs = err.get("errorMessages", [])
                        if error_msgs:
                            error_msg = ", ".join(error_msgs)
                        elif err.get("message"):
                            error_msg = err["message"]
                    except Exception:
                        pass
                    return ToolResult(
                        success=False, output="", error=f"Failed to add comment to Jira issue ({response.status_code}): {error_msg}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")