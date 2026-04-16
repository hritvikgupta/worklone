from typing import Any, Dict, List
import httpx
import re
from urllib.parse import urlparse
from datetime import datetime
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraUpdateTool(BaseTool):
    name = "jira_update"
    description = "Update a Jira issue"
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
        fetch_url = "https://api.atlassian.com/oauth/token/accessible-resources"
        fetch_headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(fetch_url, headers=fetch_headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch cloud ID: HTTP {resp.status_code} - {resp.text}")
            sites: List[Dict[str, Any]] = resp.json()
            for site in sites:
                site_url = site.get("url", "")
                parsed = urlparse(site_url)
                if parsed.netloc == domain:
                    return site["id"]
            raise ValueError(f"No accessible Jira site found for domain '{domain}'")

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
                    "description": "Jira issue key to update (e.g., PROJ-123)",
                },
                "summary": {
                    "type": "string",
                    "description": "New summary for the issue",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the issue",
                },
                "priority": {
                    "type": "string",
                    "description": "New priority ID or name for the issue (e.g., \"High\")",
                },
                "assignee": {
                    "type": "string",
                    "description": "New assignee account ID for the issue",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to set on the issue (array of label name strings)",
                },
                "components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Components to set on the issue (array of component name strings)",
                },
                "duedate": {
                    "type": "string",
                    "description": "Due date for the issue (format: YYYY-MM-DD)",
                },
                "fixVersions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fix versions to set (array of version name strings)",
                },
                "environment": {
                    "type": "string",
                    "description": "Environment information for the issue",
                },
                "customFieldId": {
                    "type": "string",
                    "description": "Custom field ID to update (e.g., customfield_10001)",
                },
                "customFieldValue": {
                    "type": "string",
                    "description": "Value for the custom field",
                },
                "notifyUsers": {
                    "type": "boolean",
                    "description": "Whether to send email notifications about this update (default: true)",
                },
            },
            "required": ["domain", "issueKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        issue_key = parameters["issueKey"]
        cloud_id = parameters.get("cloudId")
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)
        
        notify_users = parameters.get("notifyUsers", True)
        notify_param = "?notifyUsers=false" if not notify_users else ""
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}{notify_param}"
        
        fields: Dict[str, Any] = {}
        summary_value = parameters.get("summary")
        if summary_value:
            fields["summary"] = summary_value
        
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
        
        priority = parameters.get("priority")
        if priority:
            if re.match(r"^\d+$", priority):
                fields["priority"] = {"id": priority}
            else:
                fields["priority"] = {"name": priority}
        
        assignee = parameters.get("assignee")
        if assignee:
            fields["assignee"] = {"accountId": assignee}
        
        labels = parameters.get("labels")
        if labels:
            fields["labels"] = labels
        
        components = parameters.get("components")
        if components:
            fields["components"] = [{"name": name} for name in components]
        
        duedate = parameters.get("duedate")
        if duedate:
            fields["duedate"] = duedate
        
        fix_versions = parameters.get("fixVersions")
        if fix_versions:
            fields["fixVersions"] = [{"name": name} for name in fix_versions]
        
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
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                data: Dict[str, Any] | None = None
                try:
                    data = response.json()
                except:
                    data = {}
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")