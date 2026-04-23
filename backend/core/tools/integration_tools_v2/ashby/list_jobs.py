from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListJobsTool(BaseTool):
    name = "ashby_list_jobs"
    description = "Lists all jobs in an Ashby organization. By default returns Open, Closed, and Archived jobs. Specify status to filter."
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
        api_key = context.get("ASHBY_API_KEY", "") if context else ""
        return api_key.strip()

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 100)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by job status: Open, Closed, Archived, or Draft",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        auth_header = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        }

        body: Dict[str, Any] = {}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor
        per_page = parameters.get("perPage")
        if per_page is not None:
            body["limit"] = per_page
        status = parameters.get("status")
        if status:
            body["status"] = [status]

        url = "https://api.ashbyhq.com/job.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    error_msg = "Failed to list jobs"
                    error_info = data.get("errorInfo")
                    if isinstance(error_info, dict):
                        error_msg = error_info.get("message", error_msg)
                    return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")