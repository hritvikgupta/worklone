from typing import Any, Dict, Optional
from datetime import datetime, timezone
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraTransitionIssueTool(BaseTool):
    name = "jira_transition_issue"
    description = "Move a Jira issue between workflow statuses (e.g., To Do -> In Progress)"
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
                    "description": "Jira issue key to transition (e.g., PROJ-123)",
                },
                "transitionId": {
                    "type": "string",
                    "description": 'ID of the transition to execute (e.g., "11" for "To Do", "21" for "In Progress")',
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add when transitioning the issue",
                },
                "resolution": {
                    "type": "string",
                    "description": 'Resolution name to set during transition (e.g., "Fixed", "Won\'t Fix")',
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey", "transitionId"],
        }

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources: {response.status_code} - {response.text}")
            resources = response.json()
            target_url = f"https://{domain}"
            for resource in resources:
                if resource.get("url") == target_url:
                    return resource["id"]
            raise ValueError(f"No cloud ID found for domain '{domain}' (looked for '{target_url}')")

    def _build_transition_body(self, transition_id: str, comment: Optional[str], resolution: Optional[str]) -> Dict[str, Any]:
        body: Dict[str, Any] = {"transition": {"id": transition_id}}
        if resolution:
            body["fields"] = {"resolution": {"name": resolution}}
        if comment:
            body["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": comment}],
                                    },
                                ],
                            },
                        },
                    },
                ],
            }
        return body

    async def _perform_transition(
        self, cloud_id: str, issue_key: str, transition_id: str, comment: Optional[str], resolution: Optional[str], access_token: str
    ) -> tuple[Optional[str], Optional[Dict[str, str]]]:
        transitions_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/transitions"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(transitions_url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch transitions: {response.status_code} - {response.text}")
            transitions_data = response.json()
            transitions = transitions_data.get("transitions", [])
            transition = next((t for t in transitions if str(t.get("id")) == str(transition_id)), None)
            if not transition:
                raise ValueError(f"Transition ID '{transition_id}' not found in available transitions.")
            transition_name = transition.get("name")
            to_status_raw = transition.get("to")
            to_status = None
            if to_status_raw:
                to_status = {
                    "id": to_status_raw.get("id", ""),
                    "name": to_status_raw.get("name", ""),
                }
            body = self._build_transition_body(transition_id, comment, resolution)
            post_headers = headers.copy()
            post_headers["Content-Type"] = "application/json"
            post_response = await client.post(transitions_url, headers=post_headers, json=body)
            if post_response.status_code not in [200, 201, 204]:
                error_msg = post_response.text
                try:
                    err_data = post_response.json()
                    error_msgs = err_data.get("errorMessages", [])
                    if error_msgs:
                        error_msg = ", ".join(error_msgs)
                    elif "message" in err_data:
                        error_msg = err_data["message"]
                except:
                    pass
                raise ValueError(f"Failed to transition issue: {post_response.status_code} - {error_msg}")
            return transition_name, to_status

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        try:
            domain: str = parameters["domain"]
            issue_key: str = parameters["issueKey"]
            transition_id: str = parameters["transitionId"]
            comment: Optional[str] = parameters.get("comment")
            resolution: Optional[str] = parameters.get("resolution")
            cloud_id: Optional[str] = parameters.get("cloudId")
            if cloud_id is None:
                cloud_id = await self._get_cloud_id(domain, access_token)
            transition_name, to_status = await self._perform_transition(
                cloud_id, issue_key, transition_id, comment, resolution, access_token
            )
            ts = datetime.now(timezone.utc).isoformat()
            output_data = {
                "ts": ts,
                "issueKey": issue_key,
                "transitionId": transition_id,
                "transitionName": transition_name,
                "toStatus": to_status,
                "success": True,
            }
            to_status_name = to_status["name"] if to_status else "Unknown"
            summary = f"Successfully transitioned issue {issue_key} using transition '{transition_name}' to status '{to_status_name}'." if transition_name else "Successfully transitioned issue."
            return ToolResult(success=True, output=summary, data=output_data)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))