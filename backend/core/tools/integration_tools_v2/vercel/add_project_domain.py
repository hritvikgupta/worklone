from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelAddProjectDomainTool(BaseTool):
    name = "vercel_add_project_domain"
    description = "Add a domain to a Vercel project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="vercel_api_key",
                description="Vercel Access Token",
                env_var="VERCEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        if not context:
            return ""
        return context.get("vercel_api_key", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or name",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain name to add",
                },
                "redirect": {
                    "type": "string",
                    "description": "Target domain for redirect",
                },
                "redirectStatusCode": {
                    "type": "number",
                    "description": "HTTP status code for redirect (301, 302, 307, 308)",
                },
                "gitBranch": {
                    "type": "string",
                    "description": "Git branch to link the domain to",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["projectId", "domain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        project_id = parameters.get("projectId", "").strip()
        domain = parameters.get("domain", "").strip()
        team_id = parameters.get("teamId", "").strip()
        qs = f"?teamId={team_id}" if team_id else ""
        url = f"https://api.vercel.com/v10/projects/{project_id}/domains{qs}"

        body = {
            "name": domain,
        }
        if redirect := parameters.get("redirect"):
            body["redirect"] = redirect.strip()
        if redirect_status_code := parameters.get("redirectStatusCode"):
            body["redirectStatusCode"] = redirect_status_code
        if git_branch := parameters.get("gitBranch"):
            body["gitBranch"] = git_branch.strip()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")