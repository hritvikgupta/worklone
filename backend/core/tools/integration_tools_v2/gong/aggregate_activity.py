from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongAggregateActivityTool(BaseTool):
    name = "gong_aggregate_activity"
    description = "Retrieve aggregated activity statistics for users by date range from Gong."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GONG_ACCESS_KEY",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="GONG_ACCESS_KEY_SECRET",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _build_body(self, parameters: dict) -> dict:
        filter_ = {
            "fromDate": parameters["fromDate"],
            "toDate": parameters["toDate"],
        }
        if parameters.get("userIds"):
            filter_["userIds"] = [id.strip() for id in parameters["userIds"].split(",")]
        body = {"filter": filter_}
        if parameters.get("cursor"):
            body["cursor"] = parameters["cursor"]
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "userIds": {
                    "type": "string",
                    "description": "Comma-separated list of Gong user IDs (up to 20 digits each)",
                },
                "fromDate": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (inclusive, in company timezone)",
                },
                "toDate": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (exclusive, in company timezone, cannot exceed current day)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
            },
            "required": ["fromDate", "toDate"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        gong_access_key = context.get("GONG_ACCESS_KEY") if context else None
        gong_access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None

        if self._is_placeholder_token(gong_access_key) or self._is_placeholder_token(gong_access_key_secret):
            return ToolResult(success=False, output="", error="Gong credentials not configured.")

        auth_str = f"{gong_access_key}:{gong_access_key_secret}"
        auth_header = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        }

        url = "https://api.gong.io/v2/stats/activity/aggregate"
        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        data = response.json()
                        errors = data.get("errors", [])
                        error_msg = errors[0].get("message") if errors else data.get("message", "Failed to get aggregate activity")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")