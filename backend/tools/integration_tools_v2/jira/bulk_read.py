from typing import Any, Dict, List, Optional
import httpx
import urllib.parse
import json
from datetime import datetime, timezone
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraBulkReadTool(BaseTool):
    name = "jira_bulk_read"
    description = "Retrieve multiple Jira issues from a project in bulk"
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
                "projectId": {
                    "type": "string",
                    "description": "Jira project key (e.g., PROJ)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "projectId"],
        }

    def _extract_adf_text(self, adf: Any) -> str:
        def recurse(node: Any) -> str:
            if isinstance(node, str):
                return node
            if not isinstance(node, dict):
                return ""
            node_type = node.get("type")
            content = node.get("content", [])
            text_parts = [recurse(child) for child in content]
            text = "".join(text_parts)
            if node_type in ["paragraph", "heading", "blockquote", "codeBlock"]:
                text += "\n"
            elif node_type == "bulletList" or node_type == "orderedList":
                text = "\n" + text.strip() + "\n"
            elif node_type == "listItem":
                text += "\n"
            return text

        if isinstance(adf, list):
            return "".join(recurse(item) for item in adf)
        return recurse(adf)

    def _process_issue(self, issue: dict) -> dict:
        fields = issue.get("fields", {})
        status = fields.get("status", {})
        issuetype = fields.get("issuetype", {})
        priority = fields.get("priority")
        assignee = fields.get("assignee")
        return {
            "id": issue.get("id", ""),
            "key": issue.get("key", ""),
            "self": issue.get("self", ""),
            "summary": fields.get("summary", ""),
            "description": self._extract_adf_text(fields.get("description")),
            "status": {
                "id": status.get("id", ""),
                "name": status.get("name", ""),
            },
            "issuetype": {
                "id": issuetype.get("id", ""),
                "name": issuetype.get("name", ""),
            },
            "priority": {
                "id": priority.get("id", "") if priority else "",
                "name": priority.get("name", "") if priority else "",
            } if priority else None,
            "assignee": {
                "accountId": assignee.get("accountId", "") if assignee else "",
                "displayName": assignee.get("displayName", "") if assignee else "",
            } if assignee else None,
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = parameters["domain"]
        project_id = parameters["projectId"]
        cloud_id = parameters.get("cloudId")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        MAX_TOTAL = 1000
        PAGE_SIZE = 100

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if not cloud_id:
                    accessible_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                    resp = await client.get(accessible_url, headers=headers)
                    if resp.status_code != 200:
                        raise ValueError(f"Failed to fetch accessible resources: {resp.status_code} - {resp.text}")
                    accessible_resources: List[Dict] = resp.json()
                    normalized_input = f"https://{domain}".lower()
                    matched_resource = next((r for r in accessible_resources if r.get("url", "").lower() == normalized_input), None)
                    if matched_resource:
                        cloud_id = matched_resource["id"]
                    elif accessible_resources:
                        cloud_id = accessible_resources[0]["id"]
                    else:
                        raise ValueError("No Jira resources found")

                ref_trimmed = (project_id or "").strip()
                project_key = ref_trimmed
                if ref_trimmed:
                    project_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project/{urllib.parse.quote(ref_trimmed)}"
                    resp = await client.get(project_url, headers=headers)
                    if resp.status_code == 200:
                        project = resp.json()
                        project_key = project.get("key", ref_trimmed)

                jql = f"project = {project_key} ORDER BY updated DESC"
                collected: List[dict] = []
                next_page_token: Optional[str] = None
                total: Optional[int] = None

                while len(collected) < MAX_TOTAL:
                    query_params = {
                        "jql": jql,
                        "fields": "summary,description,status,issuetype,priority,assignee,created,updated",
                        "maxResults": str(PAGE_SIZE),
                    }
                    if next_page_token:
                        query_params["nextPageToken"] = next_page_token
                    params_str = urllib.parse.urlencode(query_params)
                    search_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/search/jql?{params_str}"
                    resp = await client.get(search_url, headers=headers)

                    if resp.status_code != 200:
                        try:
                            err = resp.json()
                            error_messages = err.get("errorMessages", [])
                            message = ", ".join(error_messages) if error_messages else err.get("message", resp.text)
                        except Exception:
                            message = resp.text
                        raise ValueError(f"Failed to bulk read Jira issues ({resp.status_code}): {message}")

                    page_data = resp.json()
                    issues = page_data.get("issues", [])
                    if page_data.get("total") is not None:
                        total = page_data["total"]
                    collected.extend(issues)

                    is_last = page_data.get("isLast", True)
                    next_page_token = page_data.get("nextPageToken")
                    if is_last or not next_page_token or not issues:
                        break

                output_data = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "total": total,
                    "issues": [self._process_issue(issue) for issue in collected[:MAX_TOTAL]],
                    "nextPageToken": next_page_token,
                    "isLast": not next_page_token or len(collected) >= MAX_TOTAL,
                }
                return ToolResult(success=True, output=json.dumps(output_data, indent=2), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")