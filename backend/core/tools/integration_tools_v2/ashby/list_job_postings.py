from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListJobPostingsTool(BaseTool):
    name = "ashby_list_job_postings"
    description = "Lists all job postings in Ashby."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("ASHBY_API_KEY") if context else ""
        if not api_key:
            api_key = os.getenv("ASHBY_API_KEY", "")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.ashbyhq.com/jobPosting.list"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list job postings")
                    return ToolResult(success=False, output="", error=error_msg)
                
                results = data.get("results", [])
                job_postings = [
                    {
                        "id": jp.get("id"),
                        "title": jp.get("jobTitle") or jp.get("title"),
                        "jobId": jp.get("jobId"),
                        "locationName": jp.get("locationName"),
                        "departmentName": jp.get("departmentName"),
                        "employmentType": jp.get("employmentType"),
                        "isListed": jp.get("isListed", False),
                        "publishedDate": jp.get("publishedDate"),
                    }
                    for jp in results
                ]
                result_data = {"jobPostings": job_postings}
                return ToolResult(success=True, output=response.text, data=result_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")