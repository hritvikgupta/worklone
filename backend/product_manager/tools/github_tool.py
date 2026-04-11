"""
GitHub Tool — Repository, Issues, and PR management for Katy PM Agent.
"""

import os
import httpx
from typing import Any, Optional, List
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.workflows.logger import get_logger

logger = get_logger("github_tool")


class GitHubTool(BaseTool):
    """
    GitHub integration for repository management, issues, PRs, and sync.
    """

    name = "github"
    description = "Interact with GitHub: list repos, manage issues, create PRs, sync project status."
    category = "development"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub OAuth access token for repository and issue management",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                example="ghp_xxxxxxxxxxxx",
                auth_type="api_key",
                auth_url="https://github.com/settings/tokens",
                auth_provider="github",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "list_repos",
                        "list_issues",
                        "create_issue",
                        "get_issue",
                        "close_issue",
                        "list_prs",
                        "create_pr",
                        "get_repo_info",
                        "list_branches",
                    ],
                    "description": "Action to perform",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (user or org)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue or PR number",
                },
                "title": {
                    "type": "string",
                    "description": "Title for issue or PR",
                },
                "body": {
                    "type": "string",
                    "description": "Body/description for issue or PR",
                },
                "head": {
                    "type": "string",
                    "description": "Head branch for PR",
                },
                "base": {
                    "type": "string",
                    "description": "Base branch for PR",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by state",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 100)",
                    "default": 10,
                },
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        owner = parameters.get("owner", "")
        repo = parameters.get("repo", "")
        issue_number = parameters.get("issue_number")
        title = parameters.get("title", "")
        body = parameters.get("body", "")
        head = parameters.get("head", "")
        base = parameters.get("base", "main")
        state = parameters.get("state", "open")
        per_page = parameters.get("per_page", 10)

        # Get token from env or from user's OAuth integration
        token = os.getenv("GITHUB_ACCESS_TOKEN", "")
        
        if not token and context and context.get("user_id"):
            # Fetch from user's OAuth integration
            from backend.models.auth_db import AuthDB
            db = AuthDB()
            integration = db.get_integration(context["user_id"], "github")
            if integration and integration.get("access_token"):
                token = integration["access_token"]

        if not token:
            return ToolResult(
                success=False,
                output="",
                error="GitHub access token not configured. Please connect GitHub in Integrations.",
            )

        base_url = "https://api.github.com"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # ─── List Repositories ─────────────────────────────
                if action == "list_repos":
                    if owner:
                        # Explicit org/user lookup path when owner is provided.
                        response = await client.get(
                            f"{base_url}/orgs/{owner}/repos",
                            headers=headers,
                            params={"per_page": per_page, "sort": "updated", "type": "all"},
                        )
                    else:
                        response = await client.get(
                            f"{base_url}/user/repos",
                            headers=headers,
                            params={
                                "per_page": per_page,
                                "sort": "updated",
                                "affiliation": "owner,collaborator,organization_member",
                            },
                        )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    repos = response.json()
                    if owner:
                        output = f"Found {len(repos)} repositories in {owner}:\n\n"
                    else:
                        output = f"Your {len(repos)} most recently updated repositories:\n\n"
                    for r in repos:
                        output += f"• **{r['full_name']}** - {r.get('description', 'No description')}\n"
                        output += f"  Stars: {r['stargazers_count']} | Language: {r.get('language', 'N/A')} | Updated: {r['updated_at'][:10]}\n\n"
                    return ToolResult(success=True, output=output, data={"repos": repos})

                # ─── List Issues ───────────────────────────────────
                elif action == "list_issues":
                    if not owner or not repo:
                        return ToolResult(success=False, output="", error="owner and repo required")

                    response = await client.get(
                        f"{base_url}/repos/{owner}/{repo}/issues",
                        headers=headers,
                        params={"state": state, "per_page": per_page},
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    issues = response.json()
                    output = f"Issues in {owner}/{repo} ({state}):\n\n"
                    for issue in issues:
                        output += f"#{issue['number']} **{issue['title']}** - {issue.get('user', {}).get('login', 'unknown')}\n"
                        output += f"  State: {issue['state']} | Labels: {[l['name'] for l in issue.get('labels', [])]}\n\n"
                    return ToolResult(success=True, output=output, data={"issues": issues})

                # ─── Create Issue ──────────────────────────────────
                elif action == "create_issue":
                    if not owner or not repo or not title:
                        return ToolResult(success=False, output="", error="owner, repo, and title required")

                    response = await client.post(
                        f"{base_url}/repos/{owner}/{repo}/issues",
                        headers=headers,
                        json={"title": title, "body": body},
                    )
                    if response.status_code not in (200, 201):
                        return ToolResult(success=False, output="", error=response.text)

                    issue = response.json()
                    output = f"✅ Created issue #{issue['number']} in {owner}/{repo}\n**{issue['title']}**\n{issue['html_url']}"
                    return ToolResult(success=True, output=output, data={"issue": issue})

                # ─── Get Issue ─────────────────────────────────────
                elif action == "get_issue":
                    if not owner or not repo or not issue_number:
                        return ToolResult(success=False, output="", error="owner, repo, and issue_number required")

                    response = await client.get(
                        f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                        headers=headers,
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    issue = response.json()
                    output = f"#{issue['number']} **{issue['title']}**\n"
                    output += f"State: {issue['state']} | Created: {issue['created_at'][:10]}\n"
                    output += f"Labels: {[l['name'] for l in issue.get('labels', [])]}\n\n"
                    output += f"{issue.get('body', 'No description')[:500]}"
                    return ToolResult(success=True, output=output, data={"issue": issue})

                # ─── Close Issue ───────────────────────────────────
                elif action == "close_issue":
                    if not owner or not repo or not issue_number:
                        return ToolResult(success=False, output="", error="owner, repo, and issue_number required")

                    response = await client.patch(
                        f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                        headers=headers,
                        json={"state": "closed"},
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    issue = response.json()
                    output = f"✅ Closed issue #{issue['number']} in {owner}/{repo}"
                    return ToolResult(success=True, output=output, data={"issue": issue})

                # ─── List PRs ──────────────────────────────────────
                elif action == "list_prs":
                    if not owner or not repo:
                        return ToolResult(success=False, output="", error="owner and repo required")

                    response = await client.get(
                        f"{base_url}/repos/{owner}/{repo}/pulls",
                        headers=headers,
                        params={"state": state, "per_page": per_page},
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    prs = response.json()
                    output = f"Pull Requests in {owner}/{repo} ({state}):\n\n"
                    for pr in prs:
                        output += f"#{pr['number']} **{pr['title']}** - {pr.get('user', {}).get('login', 'unknown')}\n"
                        output += f"  State: {pr['state']} | Branch: {pr['head']['ref']} → {pr['base']['ref']}\n\n"
                    return ToolResult(success=True, output=output, data={"prs": prs})

                # ─── Create PR ─────────────────────────────────────
                elif action == "create_pr":
                    if not owner or not repo or not title or not head or not base:
                        return ToolResult(success=False, output="", error="owner, repo, title, head, and base required")

                    response = await client.post(
                        f"{base_url}/repos/{owner}/{repo}/pulls",
                        headers=headers,
                        json={"title": title, "body": body, "head": head, "base": base},
                    )
                    if response.status_code not in (200, 201):
                        return ToolResult(success=False, output="", error=response.text)

                    pr = response.json()
                    output = f"✅ Created PR #{pr['number']} in {owner}/{repo}\n**{pr['title']}**\n{pr['html_url']}"
                    return ToolResult(success=True, output=output, data={"pr": pr})

                # ─── Get Repo Info ─────────────────────────────────
                elif action == "get_repo_info":
                    if not owner or not repo:
                        return ToolResult(success=False, output="", error="owner and repo required")

                    response = await client.get(
                        f"{base_url}/repos/{owner}/{repo}",
                        headers=headers,
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    r = response.json()
                    license_data = r.get("license") or {}
                    output = f"**{r['full_name']}**\n\n"
                    output += f"Description: {r.get('description', 'N/A')}\n"
                    output += f"Stars: ⭐ {r['stargazers_count']} | Forks: {r['forks_count']} | Watchers: {r['watchers_count']}\n"
                    output += f"Language: {r.get('language', 'N/A')} | License: {license_data.get('spdx_id', 'N/A')}\n"
                    output += f"Created: {r['created_at'][:10]} | Updated: {r['updated_at'][:10]}\n"
                    output += f"URL: {r['html_url']}"
                    return ToolResult(success=True, output=output, data={"repo": r})

                # ─── List Branches ─────────────────────────────────
                elif action == "list_branches":
                    if not owner or not repo:
                        return ToolResult(success=False, output="", error="owner and repo required")

                    response = await client.get(
                        f"{base_url}/repos/{owner}/{repo}/branches",
                        headers=headers,
                        params={"per_page": per_page},
                    )
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)

                    branches = response.json()
                    output = f"Branches in {owner}/{repo}:\n\n"
                    for b in branches:
                        output += f"• `{b['name']}` - Last commit: {b['commit']['sha'][:7]}\n"
                    return ToolResult(success=True, output=output, data={"branches": branches})

                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Unknown action: {action}",
                    )

        except Exception as e:
            logger.exception("GitHub tool execution failed")
            return ToolResult(success=False, output="", error=f"GitHub API error: {str(e)}")
