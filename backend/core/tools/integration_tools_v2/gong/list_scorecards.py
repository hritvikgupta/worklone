from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListScorecardsTool(BaseTool):
    name = "gong_list_scorecards"
    description = "Retrieve scorecard definitions from Gong settings."
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
            "properties": {},
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY") if context else None
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access keys not configured.")

        credentials_str = f"{access_key}:{access_key_secret}"
        auth_value = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_value}",
        }

        url = "https://api.gong.io/v2/settings/scorecards"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    scorecards = []
                    for sc in data.get("scorecards", []):
                        questions = []
                        for q in sc.get("questions", []):
                            questions.append({
                                "questionId": q.get("questionId") or "",
                                "questionText": q.get("questionText") or "",
                                "questionRevisionId": q.get("questionRevisionId"),
                                "isOverall": q.get("isOverall", False),
                                "created": q.get("created"),
                                "updated": q.get("updated"),
                                "updaterUserId": q.get("updaterUserId"),
                            })
                        scorecard = {
                            "scorecardId": sc.get("scorecardId") or "",
                            "scorecardName": sc.get("scorecardName") or "",
                            "workspaceId": sc.get("workspaceId"),
                            "enabled": sc.get("enabled", False),
                            "updaterUserId": sc.get("updaterUserId"),
                            "created": sc.get("created"),
                            "updated": sc.get("updated"),
                            "questions": questions,
                        }
                        scorecards.append(scorecard)
                    result_data = {"scorecards": scorecards}
                    return ToolResult(
                        success=True,
                        output=json.dumps(result_data),
                        data=result_data,
                    )
                else:
                    error = response.text
                    try:
                        err_data = response.json()
                        errors = err_data.get("errors", [])
                        if errors:
                            error = errors[0].get("message", error)
                        elif "message" in err_data:
                            error = err_data.get("message")
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")