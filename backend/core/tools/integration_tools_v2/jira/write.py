from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraWriteTool(BaseTool):
    name = "Jira Write"
    description = "Create a new Jira issue"
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
            context_token_keys=("provider_token",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise ValueError(f"Failed to fetch accessible resources: {response.status_code}")
                resources = response.json()
                for resource in resources:
                    resource_url = resource.get("url", "")
                    if resource_url == f"https://{domain}/" or resource_url.endswith(f"/{domain}/"):
                        return resource["id"]
                raise ValueError(f"No cloud ID found for domain {domain}")
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
                "projectId": {
                    "type": "string",
                    "description": "Jira project key (e.g., PROJ)",
                },
                "summary": {
                    "type": "string",
                    "description": "Summary for the issue",
                },
                "description": {
                    "type": "string",
                    "description": "Description for the issue",
                },
                "priority": {
                    "type": "string",
                    "description": 'Priority ID or name for the issue (e.g., "10000" or "High")',
                },
                "assignee": {
                    "type": "string",
                    "description": "Assignee account ID for the issue",
                },
                "issueType": {
                    "type": "string",
                    "description": "Type of issue to create (e.g., Task, Story, Bug, Epic, Sub-task)",
                },
                "parent": {
                    "type": "object",
                    "description": 'Parent issue key for creating subtasks (e.g., { "key": "PROJ-123" })',
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels for the issue (array of label names)",
                },
                "components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Components for the issue (array of component names)",
                },
                "duedate": {
                    "type": "string",
                    "description": "Due date for the issue (format: YYYY-MM-DD)",
                },
                "fixVersions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fix versions for the issue (array of version names)",
                },
                "reporter": {
                    "type": "string",
                    "description": "Reporter account ID for the issue",
                },
                "environment": {
                    "type": "string",
                    "description": "Environment information for the issue",
                },
                "customFieldId": {
                    "type": "string",
                    "description": "Custom field ID (e.g., customfield_10001)",
                },
                "customFieldValue": {
                    "type": "string",
                    "description": "Value for the custom field",
                },
            },
            "required": ["domain", "projectId", "summary", "issueType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        domain = parameters["domain"]
        project_id = parameters["projectId"]
        summary = parameters["summary"]
        issue_type = parameters.get("issueType", "Task")
        provided_cloud_id = parameters.get("cloudId")
        assignee = parameters.get("assignee")

        try:
            cloud_id = provided_cloud_id or await self._get_cloud_id(domain, access_token)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue"

        is_numeric_project_id = project_id.isdigit()
        fields: Dict[str, Any] = {
            "project": {"id": project_id} if is_numeric_project_id else {"key": project_id},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }

        description = parameters.get("description")
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

        parent = parameters.get("parent")
        if parent:
            fields["parent"] = parent

        priority = parameters.get("priority")
        if priority:
            is_numeric_priority = priority.isdigit()
            fields["priority"] = {"id": priority} if is_numeric_priority else {"name": priority}

        labels = parameters.get("labels", [])
        if labels:
            fields["labels"] = labels

        components = parameters.get("components", [])
        if components:
            fields["components"] = [{"name": c} for c in components]

        duedate = parameters.get("duedate")
        if duedate:
            fields["duedate"] = duedate

        fix_versions = parameters.get("fixVersions", [])
        if fix_versions:
            fields["fixVersions"] = [{"name": v} for v in fix_versions]

        reporter = parameters.get("reporter")
        if reporter:
            fields["reporter"] = {"accountId": reporter}

        environment = parameters.get("environment")
        if environment:
            fields["environment"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": environment}],
                    }
                ],
            }

        custom_field_id = parameters.get("customFieldId")
        custom_field_value = parameters.get("customFieldValue")
        if custom_field_id and custom_field_value:
            field_id = custom_field_id if custom_field_id.startswith("customfield_") else f"customfield_{custom_field_id}"
            fields[field_id] = custom_field_value

        body = {"fields": fields}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Jira API error: {response.status_code} {response.reason_phrase}",
                        data={"details": error_text},
                    )

                response_data = response.json()
                issue_key = response_data.get("key", "unknown")

                output: Dict[str, Any] = {
                    "ts": datetime.utcnow().isoformat(),
                    "id": response_data.get("id", ""),
                    "issueKey": issue_key,
                    "self": response_data.get("self", ""),
                    "summary": response_data.get("fields", {}).get("summary", summary),
                    "success": True,
                    "url": f"https://{domain}/browse/{issue_key}",
                }

                assignee_id = None
                if assignee:
                    assign_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/assignee"
                    assign_body = {"accountId": assignee}
                    assign_response = await client.put(assign_url, headers=headers, json=assign_body)
                    if assign_response.status_code in [200, 204]:
                        assignee_id = assignee

                if assignee_id:
                    output["assigneeId"] = assignee_id

                return ToolResult(success=True, output=json.dumps(output), data=output)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")