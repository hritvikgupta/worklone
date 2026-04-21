from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubTriggerWorkflowTool(BaseTool):
    name = "github_trigger_workflow"
    description = "Trigger a workflow dispatch event for a GitHub Actions workflow. The workflow must have a workflow_dispatch trigger configured. Returns 204 No Content on success."
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
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("GITHUB_ACCESS_TOKEN",),
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
                "workflow_id": {
                    "type": "string",
                    "description": 'Workflow ID (number) or workflow filename (e.g., "main.yaml")',
                },
                "ref": {
                    "type": "string",
                    "description": "Git reference (branch or tag name) to run the workflow on",
                },
                "inputs": {
                    "type": "object",
                    "description": "Input keys and values configured in the workflow file",
                },
            },
            "required": ["owner", "repo", "workflow_id", "ref"],
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
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/actions/workflows/{parameters['workflow_id']}/dispatches"
        
        body = {
            "ref": parameters["ref"],
        }
        if parameters.get("inputs"):
            body["inputs"] = parameters["inputs"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data: Dict[str, Any] = {}
                    try:
                        data = response.json()
                    except:
                        pass
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")