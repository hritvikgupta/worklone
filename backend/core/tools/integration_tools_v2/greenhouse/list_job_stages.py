from typing import Any, Dict
import httpx
import base64
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListJobStagesTool(BaseTool):
    name = "greenhouse_list_job_stages"
    description = "Lists all interview stages for a specific job in Greenhouse"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GREENHOUSE_API_KEY",
                description="Greenhouse Harvest API key",
                env_var="GREENHOUSE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "jobId": {
                    "type": "string",
                    "description": "The job ID to list stages for",
                },
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (1-500, default 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
            },
            "required": ["jobId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (context or {}).get("GREENHOUSE_API_KEY", "")
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")

        job_id = parameters["jobId"].strip()
        base_url = f"https://harvest.greenhouse.io/v1/jobs/{job_id}/stages"
        query_params = {}
        if "per_page" in parameters:
            query_params["per_page"] = str(parameters["per_page"])
        if "page" in parameters:
            query_params["page"] = str(parameters["page"])
        url = base_url
        if query_params:
            url += f"?{urlencode(query_params)}"

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code >= 200 and response.status_code < 300:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")