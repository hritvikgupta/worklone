from typing import Any, Dict, List
import httpx
import json
from datetime import datetime, timezone
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraGetUsersTool(BaseTool):
    name = "jira_get_users"
    description = "Get Jira users. If an account ID is provided, returns a single user. Otherwise, returns a list of all users."
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

    def _get_error_message(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            error_messages = data.get("errorMessages")
            if isinstance(error_messages, list):
                return ", ".join([msg for msg in error_messages if msg])
            return data.get("message") or data.get("error") or str(data)
        except Exception:
            return response.text

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Optional account ID to get a specific user. If not provided, returns all users.",
                },
                "startAt": {
                    "type": "number",
                    "description": "The index of the first user to return (for pagination, default: 0)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of users to return (default: 50)",
                },
            },
            "required": ["domain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        domain = parameters.get("domain")
        if not domain:
            return ToolResult(success=False, output="", error="Domain is required.")

        cloud_id = parameters.get("cloudId")
        account_id = parameters.get("accountId")
        start_at = parameters.get("startAt")
        max_results = parameters.get("maxResults")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if not cloud_id:
                    resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                    resp = await client.get(resources_url, headers=headers)
                    if resp.status_code != 200:
                        error_msg = self._get_error_message(resp)
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to get accessible resources ({resp.status_code}): {error_msg}",
                        )
                    resources = resp.json()
                    matching_resources = [r for r in resources if r.get("url") == f"https://{domain}"]
                    if not matching_resources:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"No accessible Jira site found for domain '{domain}'.",
                        )
                    cloud_id = matching_resources[0]["id"]

                if account_id:
                    users_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/user?accountId={urllib.parse.quote(account_id)}"
                else:
                    query_params = []
                    if start_at is not None:
                        query_params.append(f"startAt={start_at}")
                    if max_results is not None:
                        query_params.append(f"maxResults={max_results}")
                    query_string = "&".join(query_params)
                    users_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/users/search"
                    if query_string:
                        users_url += f"?{query_string}"

                resp = await client.get(users_url, headers=headers)
                if resp.status_code not in [200]:
                    error_msg = self._get_error_message(resp)
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to get Jira users ({resp.status_code}): {error_msg}",
                    )

                data = resp.json()
                if account_id:
                    users = [data] if data else []
                else:
                    users = data.get("values", [])

                def transform_user(user: dict) -> dict:
                    avatar_urls = user.get("avatarUrls", {})
                    return {
                        "accountId": user.get("accountId", ""),
                        "accountType": user.get("accountType"),
                        "active": user.get("active", False),
                        "displayName": user.get("displayName", ""),
                        "emailAddress": user.get("emailAddress"),
                        "avatarUrl": avatar_urls.get("48x48"),
                        "avatarUrls": avatar_urls,
                        "timeZone": user.get("timeZone"),
                        "self": user.get("self"),
                    }

                transformed_users = [transform_user(user) for user in users]
                output_data = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "users": transformed_users,
                    "total": len(transformed_users),
                    "startAt": start_at or 0,
                    "maxResults": max_results or 50,
                }
                output_str = json.dumps(output_data)
                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")