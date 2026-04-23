from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongInteractionStatsTool(BaseTool):
    name = "Gong Interaction Stats"
    description = "Retrieve interaction statistics for users by date range from Gong. Only includes calls with Whisper enabled."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="gong_access_key",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="gong_access_key_secret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

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
        gong_access_key = context.get("gong_access_key") if context else None
        gong_access_key_secret = context.get("gong_access_key_secret") if context else None

        if self._is_placeholder_token(gong_access_key or "") or self._is_placeholder_token(gong_access_key_secret or ""):
            return ToolResult(success=False, output="", error="Gong access credentials not configured.")

        credentials_str = f"{gong_access_key}:{gong_access_key_secret}"
        auth_value = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_value}",
        }

        filter_dict = {
            "fromDate": parameters["fromDate"],
            "toDate": parameters["toDate"],
        }
        user_ids_str = parameters.get("userIds")
        if user_ids_str:
            filter_dict["userIds"] = [uid.strip() for uid in user_ids_str.split(",") if uid.strip()]
        body = {"filter": filter_dict}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor

        url = "https://api.gong.io/v2/stats/interaction"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")