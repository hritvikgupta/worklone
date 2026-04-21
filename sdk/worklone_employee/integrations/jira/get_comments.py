from typing import Any, Dict, List, Optional
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraGetCommentsTool(BaseTool):
    name = "jira_get_comments"
    description = "Get all comments from a Jira issue"
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

    def _extract_adf_text(self, node: Any) -> str:
        if isinstance(node, str):
            return node
        if not isinstance(node, dict):
            return ""
        text = node.get("text", "")
        if text:
            return text
        content = node.get("content")
        if isinstance(content, list):
            return "".join(self._extract_adf_text(child) for child in content)
        return ""

    def _transform_user(self, user: dict | None) -> dict | None:
        if not user:
            return None
        return {
            "accountId": user.get("accountId", ""),
            "displayName": user.get("displayName", ""),
        }

    def _transform_comment(self, comment: dict) -> dict:
        author = self._transform_user(comment.get("author"))
        author_name = "Unknown"
        if comment.get("author"):
            author_name = comment["author"].get("displayName") or comment["author"].get("accountId") or "Unknown"
        update_author = self._transform_user(comment.get("updateAuthor"))
        visibility = None
        if comment.get("visibility"):
            visibility = {
                "type": comment["visibility"].get("type", ""),
                "value": comment["visibility"].get("value", ""),
            }
        return {
            "id": comment.get("id", ""),
            "body": self._extract_adf_text(comment.get("body", {})),
            "author": author or {"accountId": "", "displayName": ""},
            "authorName": author_name,
            "updateAuthor": update_author,
            "created": comment.get("created", ""),
            "updated": comment.get("updated", ""),
            "visibility": visibility,
        }

    def _get_error_message(self, response: httpx.Response) -> str:
        message = response.text[:500]
        try:
            err_data = response.json()
            if "errorMessages" in err_data and isinstance(err_data["errorMessages"], list):
                message = ", ".join(err_data["errorMessages"])
            elif "message" in err_data:
                message = err_data["message"]
        except Exception:
            pass
        return f"HTTP {response.status_code}: {message}"

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
                    "description": "Jira issue key to get comments from (e.g., PROJ-123)",
                },
                "startAt": {
                    "type": "number",
                    "description": "Index of the first comment to return (default: 0)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of comments to return (default: 50)",
                },
                "orderBy": {
                    "type": "string",
                    "description": 'Sort order for comments: "-created" for newest first, "created" for oldest first',
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        domain: str = parameters["domain"]
        issue_key: str = parameters["issueKey"]
        start_at: int = parameters.get("startAt", 0)
        max_results: int = parameters.get("maxResults", 50)
        order_by: str = parameters.get("orderBy", "-created")
        cloud_id: Optional[str] = parameters.get("cloudId")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if cloud_id:
                    url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment?startAt={start_at}&maxResults={max_results}&orderBy={order_by}"
                    response = await client.get(url, headers=headers)
                    if response.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=self._get_error_message(response),
                        )
                    data = response.json()
                else:
                    resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                    resources_resp = await client.get(resources_url, headers=headers)
                    if resources_resp.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to get accessible resources: {self._get_error_message(resources_resp)}",
                        )
                    resources = resources_resp.json()
                    cloud_id = None
                    for resource in resources:
                        resource_url = resource.get("url", "")
                        if domain in resource_url:
                            cloud_id = resource["id"]
                            break
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"No cloud ID found for domain '{domain}'. Please check the domain or provide cloudId.",
                        )
                    url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/comment?startAt={start_at}&maxResults={max_results}&orderBy={order_by}"
                    response = await client.get(url, headers=headers)
                    if response.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=self._get_error_message(response),
                        )
                    data = response.json()

                transformed_comments = [
                    self._transform_comment(comment) for comment in data.get("comments", [])
                ]
                output_data = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "issueKey": issue_key,
                    "total": data.get("total", 0),
                    "startAt": data.get("startAt", 0),
                    "maxResults": data.get("maxResults", 0),
                    "comments": transformed_comments,
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")