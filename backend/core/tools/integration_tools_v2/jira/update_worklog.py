from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraUpdateWorklogTool(BaseTool):
    name = "jira_update_worklog"
    description = "Update an existing worklog entry on a Jira issue"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="Access token",
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

    def _build_worklog_body(self, params: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        time_spent = params.get("timeSpentSeconds")
        if time_spent is not None:
            body["timeSpentSeconds"] = int(float(time_spent))
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
                                "text": comment,
                            }
                        ],
                    }
                ],
            }
        started = params.get("started")
        if started:
            if started.endswith("Z"):
                started = started[:-1] + "+0000"
            body["started"] = started
        visibility = params.get("visibility")
        if visibility:
            body["visibility"] = visibility
        return body

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            resources = resp.json()
            normalized_domain = domain.rstrip("/")
            for resource in resources:
                resource_url = resource.get("url", "").rstrip("/")
                if resource_url.endswith(normalized_domain):
                    return resource["id"]
            raise ValueError(f"No accessible Jira site found for domain '{domain}'.")

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
                    "description": "ID of the worklog entry to update",
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
                    "description": "Optional start time in ISO format",
                },
                "visibility": {
                    "type": "object",
                    "description": 'Restrict worklog visibility. Object with "type" ("role" or "group") and "value" (role/group name).',
                    "properties": {
                        "type": {"type": "string", "enum": ["role", "group"]},
                        "value": {"type": "string"},
                    },
                },
            },
            "required": ["domain", "issueKey", "worklogId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = parameters.get("domain")
        issue_key = parameters.get("issueKey")
        worklog_id = parameters.get("worklogId")
        if not all([domain, issue_key, worklog_id]):
            return ToolResult(
                success=False, output="", error="Missing required parameters: domain, issueKey, worklogId."
            )

        cloud_id = parameters.get("cloudId")
        if not cloud_id:
            try:
                cloud_id = await self._get_cloud_id(domain, access_token)
            except ValueError as e:
                return ToolResult(success=False, output="", error=str(e))

        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/worklog/{worklog_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        body = self._build_worklog_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201]:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if isinstance(err_data, dict):
                            if "errorMessages" in err_data and isinstance(err_data["errorMessages"], list):
                                error_msg = ", ".join(err_data["errorMessages"])
                            elif "message" in err_data:
                                error_msg = err_data["message"]
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to update worklog on Jira issue ({response.status_code}): {error_msg}",
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")