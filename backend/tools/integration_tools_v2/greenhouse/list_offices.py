from typing import Any, Dict
import httpx
import base64
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListOfficesTool(BaseTool):
    name = "greenhouse_list_offices"
    description = "Lists all offices configured in Greenhouse"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        if context:
            candidate = context.get("GREENHOUSE_API_KEY")
            if candidate and not self._is_placeholder_token(candidate):
                return candidate
        candidate = os.getenv("GREENHOUSE_API_KEY")
        if candidate and not self._is_placeholder_token(candidate):
            return candidate
        return ""

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
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        if not api_key:
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
            "Content-Type": "application/json",
        }

        url = "https://harvest.greenhouse.io/v1/offices"
        params: Dict[str, Any] = {}
        per_page = parameters.get("per_page")
        if per_page is not None:
            params["per_page"] = per_page
        page = parameters.get("page")
        if page is not None:
            params["page"] = page

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")