from typing import Any, Dict
import httpx
import os
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabCreatePipelineTool(BaseTool):
    name = "gitlab_create_pipeline"
    description = "Trigger a new pipeline in a GitLab project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITLAB_ACCESS_TOKEN",
                description="GitLab Personal Access Token",
                env_var="GITLAB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token_key = "GITLAB_ACCESS_TOKEN"
        token = context.get(token_key) if context else None
        if token is None:
            token = os.getenv(token_key)
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch or tag to run the pipeline on",
                },
                "variables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                            },
                            "value": {
                                "type": "string",
                            },
                            "variable_type": {
                                "type": "string",
                            },
                        },
                        "required": ["key", "value"],
                    },
                    "description": "Array of variables for the pipeline (each with key, value, and optional variable_type)",
                },
            },
            "required": ["projectId", "ref"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "PRIVATE-TOKEN": access_token,
            "Content-Type": "application/json",
        }

        encoded_project_id = quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/pipeline"

        body = {
            "ref": parameters["ref"],
        }
        variables = parameters.get("variables")
        if variables and len(variables) > 0:
            body["variables"] = variables

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"GitLab API error ({response.status_code}): {response.text}",
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")