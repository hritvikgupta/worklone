from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraAddWorklogTool(BaseTool):
    name = "jira_add_worklog"
    description = "Add a time tracking worklog entry to a Jira issue"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_DOMAIN",
                description="Your Jira domain (e.g., yourcompany.atlassian.net)",
                env_var="JIRA_DOMAIN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="Access token",
                env_var="JIRA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
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
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                sites = response.json()
                domain_normalized = domain.lower().strip().rstrip("/")
                for site in sites:
                    site_url = site.get("url", "").lower().rstrip("/")
                    if site_url.endswith(domain_normalized):
                        return site["id"]
                raise ValueError(f"No matching cloud ID found for domain '{domain}'")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch accessible resources: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Error getting cloud ID: {str(e)}")

    def _build_worklog_body(self, params: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "timeSpentSeconds": int(params["timeSpentSeconds"]),
        }
        comment = params.get("comment")
        if comment:
            body["comment"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": str(comment),
                            }
                        ],
                    }
                ],
            }
        started_str = params.get("started")
        if started_str:
            if isinstance(started_str, str) and started_str.endswith("Z"):
                started_str = started_str[:-1] + "+0000"
            body["started"] = started_str
        else:
            now = datetime.now(timezone.utc).isoformat()
            body["started"] = now[:-1] + "+0000"
        visibility = params.get("visibility")
        if visibility:
            body["visibility"] = visibility
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "issueKey": {
                    "type": "string",
                    "description": "Jira issue key to add worklog to (e.g., PROJ-123)",
                },
                "timeSpentSeconds": {
                    "type": "number",
                    "description": "Time spent in seconds",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment for the worklog entry",
                },
                "started": {
                    "type": "string",
                    "description": "Optional start time in ISO format (defaults to current time)",
                },
                "visibility": {
                    "type": "object",
                    "description": 'Restrict worklog visibility. Object with "type" ("role" or "group") and "value" (role/group name).',
                },
            },
            "required": ["issueKey", "timeSpentSeconds"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        domain = context.get("JIRA_DOMAIN") if context else None
        domain = (domain or "").strip()
        if self._is_placeholder_token(domain):
            return ToolResult(success=False, output="", error="Jira domain not configured.")

        time_spent_seconds = parameters.get("timeSpentSeconds")
        if time_spent_seconds is None or time_spent_seconds <= 0:
            return ToolResult(
                success=False, output="", error="timeSpentSeconds is required and must be greater than 0"
            )

        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        cloud_id = context.get("cloudId")
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)

        issue_key = parameters["issueKey"]
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/worklog"

        body = self._build_worklog_body(parameters)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True, output=response.text, data=response.json()
                    )
                else:
                    try:
                        err_data = response.json()
                        error_msgs = err_data.get("errorMessages", [])
                        error_msg = (
                            ", ".join(error_msgs)
                            if error_msgs
                            else err_data.get("message", response.text)
                        )
                    except Exception:
                        error_msg = response.text or f"HTTP error {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")