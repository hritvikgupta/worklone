from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbyGetJobPostingTool(BaseTool):
    name = "ashby_get_job_posting"
    description = "Retrieves full details about a single job posting by its ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "ashby",
            context=context,
            context_token_keys=("ASHBY_API_KEY",),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "jobPostingId": {
                    "type": "string",
                    "description": "The UUID of the job posting to fetch",
                },
            },
            "required": ["jobPostingId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/jobPosting.info"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"jobPostingId": parameters["jobPostingId"]},
                )
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to get job posting")
                    return ToolResult(success=False, output="", error=error_msg)
                
                r = data.get("results", {})
                output = {
                    "id": r.get("id"),
                    "title": r.get("jobTitle") or r.get("title"),
                    "jobId": r.get("jobId"),
                    "locationName": r.get("locationName"),
                    "departmentName": r.get("departmentName"),
                    "employmentType": r.get("employmentType"),
                    "descriptionPlain": r.get("descriptionPlain") or r.get("description"),
                    "isListed": r.get("isListed", False),
                    "publishedDate": r.get("publishedDate"),
                    "externalLink": r.get("externalLink"),
                }
                
                return ToolResult(success=True, output=response.text, data=output)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")