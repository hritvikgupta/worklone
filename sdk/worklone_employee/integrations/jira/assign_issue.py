from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraAssignIssueTool(BaseTool):
    name = "jira_assign_issue"
    description = "Assign a Jira issue to a user"
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
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            resources: list[dict] = resp.json()
            for resource in resources:
                resource_url = resource.get("url", "")
                if "/ex/jira/" in resource_url:
                    return resource["id"]
            raise ValueError("No Jira Cloud ID found in accessible resources.")

    async def _assign_issue(self, cloud_id: str, issue_key: str, account_id_str: str, access_token: str) -> httpx.Response:
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/assignee"
        body = {"accountId": None if account_id_str == "null" else account_id_str}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.put(url, headers=headers, json=body)

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
                    "description": "Jira issue key to assign (e.g., PROJ-123)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Account ID of the user to assign the issue to. Use \"-1\" for automatic assignment or null to unassign.",
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

        params = parameters
        issue_key = params["issueKey"]
        account_id_str = params["accountId"]
        domain = params["domain"]
        cloud_id = params.get("cloudId")

        try:
            if not cloud_id:
                cloud_id = await self._get_cloud_id(domain, access_token)

            response = await self._assign_issue(cloud_id, issue_key, account_id_str, access_token)

            if response.status_code not in [200, 201, 204]:
                error_msg = response.text
                try:
                    err_data = response.json()
                    if "errorMessages" in err_data:
                        error_msg = ", ".join(err_data["errorMessages"])
                    elif "message" in err_data:
                        error_msg = err_data["message"]
                except:
                    pass
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to assign Jira issue ({response.status_code}): {error_msg}",
                )

            ts = datetime.now(timezone.utc).isoformat()
            output_data = {
                "ts": ts,
                "issueKey": issue_key,
                "assigneeId": account_id_str,
                "success": True,
            }
            return ToolResult(
                success=True,
                output=json.dumps(output_data),
                data=output_data,
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")