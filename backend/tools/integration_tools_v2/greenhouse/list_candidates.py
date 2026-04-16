from typing import Any, Dict
import httpx
import base64
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListCandidatesTool(BaseTool):
    name = "greenhouse_list_candidates"
    description = "Lists candidates from Greenhouse with optional filtering by date, job, or email"
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
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (1-500, default 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
                "created_after": {
                    "type": "string",
                    "description": "Return only candidates created at or after this ISO 8601 timestamp",
                },
                "created_before": {
                    "type": "string",
                    "description": "Return only candidates created before this ISO 8601 timestamp",
                },
                "updated_after": {
                    "type": "string",
                    "description": "Return only candidates updated at or after this ISO 8601 timestamp",
                },
                "updated_before": {
                    "type": "string",
                    "description": "Return only candidates updated before this ISO 8601 timestamp",
                },
                "job_id": {
                    "type": "string",
                    "description": "Filter to candidates who applied to this job ID (excludes prospects)",
                },
                "email": {
                    "type": "string",
                    "description": "Filter to candidates with this email address",
                },
                "candidate_ids": {
                    "type": "string",
                    "description": "Comma-separated candidate IDs to retrieve (max 50)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("GREENHOUSE_API_KEY") if context else None
        api_key = api_key or os.getenv("GREENHOUSE_API_KEY")

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
            "Content-Type": "application/json",
        }

        url = "https://harvest.greenhouse.io/v1/candidates"

        query_params = {
            "per_page": parameters.get("per_page"),
            "page": parameters.get("page"),
            "created_after": parameters.get("created_after"),
            "created_before": parameters.get("created_before"),
            "updated_after": parameters.get("updated_after"),
            "updated_before": parameters.get("updated_before"),
            "job_id": parameters.get("job_id"),
            "candidate_ids": parameters.get("candidate_ids"),
        }
        email = parameters.get("email")
        if email is not None:
            query_params["email_address"] = email
        query_params = {k: v for k, v in query_params.items() if v is not None}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if 200 <= response.status_code < 300:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")