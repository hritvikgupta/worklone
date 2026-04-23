from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListOpeningsTool(BaseTool):
    name = "ashby_list_openings"
    description = "Lists all openings in Ashby with pagination."
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
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ASHBY_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        auth_value = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_value}",
        }

        body: Dict[str, Any] = {}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor
        per_page = parameters.get("perPage")
        if per_page is not None:
            body["limit"] = per_page

        url = "https://api.ashbyhq.com/opening.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")