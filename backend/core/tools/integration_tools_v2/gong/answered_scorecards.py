from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongAnsweredScorecardsTool(BaseTool):
    name = "gong_answered_scorecards"
    description = "Retrieve answered scorecards for reviewed users or by date range from Gong."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "callFromDate": {
                    "type": "string",
                    "description": "Start date for calls in YYYY-MM-DD format (inclusive, in company timezone). Defaults to earliest recorded call.",
                },
                "callToDate": {
                    "type": "string",
                    "description": "End date for calls in YYYY-MM-DD format (exclusive, in company timezone). Defaults to latest recorded call.",
                },
                "reviewFromDate": {
                    "type": "string",
                    "description": "Start date for reviews in YYYY-MM-DD format (inclusive, in company timezone). Defaults to earliest reviewed call.",
                },
                "reviewToDate": {
                    "type": "string",
                    "description": "End date for reviews in YYYY-MM-DD format (exclusive, in company timezone). Defaults to latest reviewed call.",
                },
                "scorecardIds": {
                    "type": "string",
                    "description": "Comma-separated list of scorecard IDs to filter by",
                },
                "reviewedUserIds": {
                    "type": "string",
                    "description": "Comma-separated list of reviewed user IDs to filter by",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY") if context else None
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Access credentials not configured.")

        filter_: Dict[str, Any] = {}
        call_from_date = parameters.get("callFromDate")
        if call_from_date:
            filter_["callFromDate"] = call_from_date
        call_to_date = parameters.get("callToDate")
        if call_to_date:
            filter_["callToDate"] = call_to_date
        review_from_date = parameters.get("reviewFromDate")
        if review_from_date:
            filter_["reviewFromDate"] = review_from_date
        review_to_date = parameters.get("reviewToDate")
        if review_to_date:
            filter_["reviewToDate"] = review_to_date
        scorecard_ids = parameters.get("scorecardIds")
        if scorecard_ids:
            filter_["scorecardIds"] = [id_.strip() for id_ in str(scorecard_ids).split(",")]
        reviewed_user_ids = parameters.get("reviewedUserIds")
        if reviewed_user_ids:
            filter_["reviewedUserIds"] = [id_.strip() for id_ in str(reviewed_user_ids).split(",")]

        body: Dict[str, Any] = {"filter": filter_}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor

        auth = base64.b64encode(f"{access_key}:{access_key_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        }
        url = "https://api.gong.io/v2/stats/activity/scorecards"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")