from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubUpdateBranchProtectionTool(BaseTool):
    name = "github_update_branch_protection"
    description = "Update branch protection rules for a specific branch, including status checks, review requirements, admin enforcement, and push restrictions."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name",
                },
                "required_status_checks": {
                    "type": "object",
                    "description": "Required status check configuration (null to disable). Object with strict (boolean) and contexts (string array)",
                },
                "enforce_admins": {
                    "type": "boolean",
                    "description": "Whether to enforce restrictions for administrators",
                },
                "required_pull_request_reviews": {
                    "type": "object",
                    "description": "PR review requirements (null to disable). Object with optional required_approving_review_count, dismiss_stale_reviews, require_code_owner_reviews",
                },
                "restrictions": {
                    "type": "object",
                    "description": "Push restrictions (null to disable). Object with users (string array) and teams (string array)",
                },
            },
            "required": [
                "owner",
                "repo",
                "branch",
                "required_status_checks",
                "enforce_admins",
                "required_pull_request_reviews",
                "restrictions",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/branches/{parameters['branch']}/protection"
        
        body = {
            "required_status_checks": parameters["required_status_checks"],
            "enforce_admins": parameters["enforce_admins"],
            "required_pull_request_reviews": parameters["required_pull_request_reviews"],
            "restrictions": parameters["restrictions"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")