"""
Jira Tool — Project management integration for backlog, sprints, and issues.
"""

import os
import json
import httpx
from typing import Any, Optional, Dict
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraTool(BaseTool):
    """
    Jira integration for product backlog management.
    
    Supports:
    - Creating and updating issues (stories, bugs, tasks, epics)
    - Managing sprints and backlog
    - Searching and filtering issues
    - Getting project information
    """
    
    name = "jira"
    description = "Manage Jira issues, backlog, and sprints. Create user stories, track bugs, plan releases."
    category = "project_management"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="Jira OAuth connection in Integrations (recommended)",
                env_var="JIRA_ACCESS_TOKEN",
                required=True,
                example="OAuth token via Integrations",
                auth_type="oauth",
                auth_provider="jira",
            ),
            CredentialRequirement(
                key="JIRA_BASE_URL",
                description="Fallback Jira base URL for server-level API token auth",
                env_var="JIRA_BASE_URL",
                required=False,
                example="https://acme.atlassian.net",
            ),
        ]
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": [
                        "create_issue",
                        "update_issue",
                        "search_issues",
                        "get_issue",
                        "add_comment",
                        "get_backlog",
                        "get_sprints",
                        "get_projects",
                    ],
                },
                # Create issue params
                "project_key": {
                    "type": "string",
                    "description": "Project key (e.g., 'PROJ', 'ENG')",
                },
                "issue_type": {
                    "type": "string",
                    "description": "Issue type",
                    "enum": ["Story", "Bug", "Task", "Epic", "Sub-task"],
                },
                "summary": {
                    "type": "string",
                    "description": "Issue title/summary",
                },
                "description": {
                    "type": "string",
                    "description": "Issue description",
                },
                "priority": {
                    "type": "string",
                    "description": "Issue priority",
                    "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                },
                "assignee": {
                    "type": "string",
                    "description": "Email or username of assignee",
                },
                "labels": {
                    "type": "array",
                    "description": "Labels to add",
                    "items": {"type": "string"},
                },
                # Update/search params
                "issue_key": {
                    "type": "string",
                    "description": "Issue key (e.g., 'PROJ-123')",
                },
                "jql": {
                    "type": "string",
                    "description": "JQL query for searching issues",
                },
                "comment": {
                    "type": "string",
                    "description": "Comment text to add",
                },
                # Search params
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10,
                },
                # Sprint params
                "board_id": {
                    "type": "string",
                    "description": "Board ID for sprint operations",
                },
            },
            "required": ["action"],
        }
    
    def _get_credentials(self, context: dict = None) -> tuple:
        """Get Jira credentials from OAuth integration (preferred) or env/context fallback."""
        base_url = os.getenv("JIRA_BASE_URL", "")
        api_token = os.getenv("JIRA_API_TOKEN", "")
        email = os.getenv("JIRA_EMAIL", "")
        oauth_token = ""
        cloud_id = ""
        provider_site_url = ""
        
        if context:
            base_url = context.get("jira_base_url", base_url)
            api_token = context.get("jira_api_token", api_token)
            email = context.get("jira_email", email)
        
        if context and context.get("user_id"):
            from backend.models.auth_db import AuthDB
            db = AuthDB()
            integration = db.get_integration(context["user_id"], "jira")
            if integration and integration.get("access_token"):
                oauth_token = str(integration.get("access_token") or "")
                raw_metadata = integration.get("metadata")
                if raw_metadata:
                    try:
                        metadata = json.loads(raw_metadata)
                    except (TypeError, json.JSONDecodeError):
                        metadata = {}
                    cloud_id = str(metadata.get("cloud_id") or "")
                    provider_site_url = str(metadata.get("site_url") or "")
        
        return base_url, api_token, email, oauth_token, cloud_id, provider_site_url

    async def _resolve_jira_resource(
        self, oauth_token: str, preferred_site_url: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Resolve Atlassian cloud resource for Jira OAuth."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={
                    "Authorization": f"Bearer {oauth_token}",
                    "Accept": "application/json",
                },
            )
            if response.status_code != 200:
                return None

            resources = response.json()
            if not isinstance(resources, list) or not resources:
                return None

            if preferred_site_url:
                normalized = preferred_site_url.rstrip("/").lower()
                for resource in resources:
                    url = str(resource.get("url") or "").rstrip("/").lower()
                    if url == normalized:
                        return resource

            return resources[0]

    def _get_auth_headers(self, email: str, api_token: str) -> dict:
        """Get authentication headers for Jira API."""
        import base64
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        action = parameters.get("action")
        
        base_url, api_token, email, oauth_token, cloud_id, provider_site_url = self._get_credentials(context)
        headers: dict

        if oauth_token:
            if not cloud_id:
                resource = await self._resolve_jira_resource(
                    oauth_token,
                    preferred_site_url=base_url or provider_site_url,
                )
                if not resource:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Jira OAuth connected but no accessible Jira site found. Reconnect Jira and grant site access.",
                    )

                cloud_id = str(resource.get("id") or "")
                provider_site_url = str(resource.get("url") or "")

                if context and context.get("user_id") and cloud_id:
                    from backend.models.auth_db import AuthDB
                    db = AuthDB()
                    integration = db.get_integration(context["user_id"], "jira")
                    if integration:
                        existing_metadata = {}
                        raw_metadata = integration.get("metadata")
                        if raw_metadata:
                            try:
                                existing_metadata = json.loads(raw_metadata)
                            except (TypeError, json.JSONDecodeError):
                                existing_metadata = {}
                        existing_metadata.update(
                            {
                                "cloud_id": cloud_id,
                                "site_url": provider_site_url,
                                "site_name": resource.get("name"),
                                "scopes": resource.get("scopes", []),
                            }
                        )
                        db.save_integration(
                            user_id=context["user_id"],
                            provider="jira",
                            access_token=integration.get("access_token") or oauth_token,
                            refresh_token=integration.get("refresh_token"),
                            token_expires_at=integration.get("token_expires_at"),
                            scopes=integration.get("scopes"),
                            provider_user_id=integration.get("provider_user_id"),
                            provider_email=integration.get("provider_email"),
                            metadata=json.dumps(existing_metadata),
                        )

            if not cloud_id:
                return ToolResult(
                    success=False,
                    output="",
                    error="Jira OAuth connected but cloud id is missing. Reconnect Jira in Integrations.",
                )

            base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"
            headers = {
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        elif not base_url or not api_token or not email:
            return ToolResult(
                success=False,
                output="",
                error="Jira not connected. Connect Jira in Integrations, or set JIRA_BASE_URL, JIRA_API_TOKEN, and JIRA_EMAIL.",
            )
        else:
            headers = self._get_auth_headers(email, api_token)
        
        try:
            if action == "create_issue":
                return await self._create_issue(parameters, base_url, headers)
            elif action == "update_issue":
                return await self._update_issue(parameters, base_url, headers)
            elif action == "search_issues":
                return await self._search_issues(parameters, base_url, headers)
            elif action == "get_issue":
                return await self._get_issue(parameters, base_url, headers)
            elif action == "add_comment":
                return await self._add_comment(parameters, base_url, headers)
            elif action == "get_backlog":
                return await self._get_backlog(parameters, base_url, headers)
            elif action == "get_sprints":
                return await self._get_sprints(parameters, base_url, headers)
            elif action == "get_projects":
                return await self._get_projects(base_url, headers)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}",
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Jira API error: {str(e)}",
            )
    
    async def _create_issue(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Create a new Jira issue."""
        project_key = params.get("project_key")
        issue_type = params.get("issue_type", "Story")
        summary = params.get("summary")
        description = params.get("description", "")
        priority = params.get("priority")
        assignee = params.get("assignee")
        labels = params.get("labels", [])
        
        if not project_key or not summary:
            return ToolResult(
                success=False,
                output="",
                error="project_key and summary are required",
            )
        
        # Build issue data
        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        }
        
        if priority:
            fields["priority"] = {"name": priority}
        
        if assignee:
            fields["assignee"] = {"emailAddress": assignee}
        
        if labels:
            fields["labels"] = labels
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/rest/api/3/issue",
                headers=headers,
                json={"fields": fields},
            )
            
            if response.status_code == 201:
                data = response.json()
                issue_key = data.get("key")
                return ToolResult(
                    success=True,
                    output=f"Created {issue_type}: {issue_key} - {summary}",
                    data=data,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to create issue: {response.text}",
                )
    
    async def _update_issue(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Update an existing Jira issue."""
        issue_key = params.get("issue_key")
        summary = params.get("summary")
        description = params.get("description")
        priority = params.get("priority")
        status = params.get("status")
        
        if not issue_key:
            return ToolResult(
                success=False,
                output="",
                error="issue_key is required",
            )
        
        fields = {}
        if summary:
            fields["summary"] = summary
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
        if priority:
            fields["priority"] = {"name": priority}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{base_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                json={"fields": fields},
            )
            
            if response.status_code == 204:
                return ToolResult(
                    success=True,
                    output=f"Updated {issue_key}",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to update issue: {response.text}",
                )
    
    async def _search_issues(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Search issues using JQL."""
        jql = params.get("jql", "assignee = currentUser() ORDER BY created DESC")
        max_results = params.get("max_results", 10)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/api/3/search",
                headers=headers,
                params={"jql": jql, "maxResults": max_results},
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                
                output = f"Found {len(issues)} issues:\n\n"
                for issue in issues:
                    key = issue.get("key")
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", "No summary")
                    status = fields.get("status", {}).get("name", "Unknown")
                    output += f"• {key}: {summary} [{status}]\n"
                
                return ToolResult(
                    success=True,
                    output=output,
                    data=issues,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Search failed: {response.text}",
                )
    
    async def _get_issue(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Get details of a specific issue."""
        issue_key = params.get("issue_key")
        
        if not issue_key:
            return ToolResult(
                success=False,
                output="",
                error="issue_key is required",
            )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                fields = data.get("fields", {})
                
                output = f"""Issue: {data.get('key')}
Summary: {fields.get('summary')}
Type: {fields.get('issuetype', {}).get('name')}
Status: {fields.get('status', {}).get('name')}
Priority: {fields.get('priority', {}).get('name')}
Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned')}
Reporter: {fields.get('reporter', {}).get('displayName')}
Created: {fields.get('created', 'Unknown')[:10]}
Updated: {fields.get('updated', 'Unknown')[:10]}

Description:
{self._extract_text(fields.get('description', {}))}
"""
                return ToolResult(
                    success=True,
                    output=output,
                    data=data,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to get issue: {response.text}",
                )
    
    async def _add_comment(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Add a comment to an issue."""
        issue_key = params.get("issue_key")
        comment = params.get("comment")
        
        if not issue_key or not comment:
            return ToolResult(
                success=False,
                output="",
                error="issue_key and comment are required",
            )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": comment}],
                            }
                        ],
                    }
                },
            )
            
            if response.status_code == 201:
                return ToolResult(
                    success=True,
                    output=f"Comment added to {issue_key}",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to add comment: {response.text}",
                )
    
    async def _get_backlog(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Get backlog issues for a project."""
        project_key = params.get("project_key")
        
        jql = "status = Backlog"
        if project_key:
            jql += f" AND project = {project_key}"
        jql += " ORDER BY priority DESC, created DESC"
        
        return await self._search_issues(
            {"jql": jql, "max_results": params.get("max_results", 20)},
            base_url,
            headers,
        )
    
    async def _get_sprints(
        self, params: dict, base_url: str, headers: dict
    ) -> ToolResult:
        """Get active sprints (requires Agile API)."""
        board_id = params.get("board_id")
        
        # If no board_id, list boards first
        if not board_id:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/rest/agile/1.0/board",
                    headers=headers,
                    params={"maxResults": 10},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    boards = data.get("values", [])
                    
                    output = "Available boards:\n"
                    for board in boards:
                        output += f"• {board.get('name')} (ID: {board.get('id')})\n"
                    
                    return ToolResult(
                        success=True,
                        output=output,
                        data=boards,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to get boards: {response.text}",
                    )
        
        # Get sprints for specific board
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/agile/1.0/board/{board_id}/sprint",
                headers=headers,
                params={"state": "active,future"},
            )
            
            if response.status_code == 200:
                data = response.json()
                sprints = data.get("values", [])
                
                output = f"Sprints for board {board_id}:\n"
                for sprint in sprints:
                    output += f"• {sprint.get('name')} ({sprint.get('state')})\n"
                
                return ToolResult(
                    success=True,
                    output=output,
                    data=sprints,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to get sprints: {response.text}",
                )
    
    async def _get_projects(self, base_url: str, headers: dict) -> ToolResult:
        """Get list of accessible projects."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/api/3/project",
                headers=headers,
                params={"maxResults": 20},
            )
            
            if response.status_code == 200:
                data = response.json()
                projects = data  # API returns array directly
                
                output = "Accessible projects:\n"
                for project in projects:
                    key = project.get("key")
                    name = project.get("name")
                    output += f"• {key}: {name}\n"
                
                return ToolResult(
                    success=True,
                    output=output,
                    data=projects,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to get projects: {response.text}",
                )
    
    def _extract_text(self, description: dict) -> str:
        """Extract text from Atlassian Document Format."""
        if not description:
            return "No description"
        
        content = description.get("content", [])
        texts = []
        
        for block in content:
            if block.get("type") == "paragraph":
                for item in block.get("content", []):
                    if item.get("type") == "text":
                        texts.append(item.get("text", ""))
        
        return " ".join(texts) if texts else "(Complex description)"
