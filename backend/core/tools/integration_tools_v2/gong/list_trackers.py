from typing import Any, Dict, List
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListTrackersTool(BaseTool):
    name = "gong_list_trackers"
    description = "Retrieve smart tracker and keyword tracker definitions from Gong settings."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKey",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="accessKeySecret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    async def _resolve_credentials(self, context: Dict | None) -> tuple[str, str]:
        access_key = context.get("accessKey") if context else os.getenv("GONG_ACCESS_KEY", "")
        access_key_secret = context.get("accessKeySecret") if context else os.getenv("GONG_ACCESS_KEY_SECRET", "")
        return access_key, access_key_secret

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspaceId": {
                    "type": "string",
                    "description": "The ID of the workspace the keyword trackers are in. When empty, all trackers in all workspaces are returned.",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key, access_key_secret = await self._resolve_credentials(context)

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access credentials not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_key}:{access_key_secret}'.encode('utf-8')).decode('utf-8')}",
        }

        url = "https://api.gong.io/v2/settings/trackers"
        query_params = {}
        workspace_id = parameters.get("workspaceId")
        if workspace_id:
            query_params["workspaceId"] = workspace_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    trackers = []
                    keyword_trackers = data.get("keywordTrackers", [])
                    for t in keyword_trackers:
                        trackers.append({
                            "trackerId": t.get("trackerId", ""),
                            "trackerName": t.get("trackerName", ""),
                            "workspaceId": t.get("workspaceId"),
                            "languageKeywords": [
                                {
                                    "language": lk.get("language"),
                                    "keywords": lk.get("keywords", []),
                                    "includeRelatedForms": lk.get("includeRelatedForms", False),
                                }
                                for lk in t.get("languageKeywords", [])
                            ],
                            "affiliation": t.get("affiliation"),
                            "partOfQuestion": t.get("partOfQuestion"),
                            "saidAt": t.get("saidAt"),
                            "saidAtInterval": t.get("saidAtInterval"),
                            "saidAtUnit": t.get("saidAtUnit"),
                            "saidInTopics": t.get("saidInTopics", []),
                            "saidInCallParts": t.get("saidInCallParts", []),
                            "filterQuery": t.get("filterQuery"),
                            "created": t.get("created"),
                            "creatorUserId": t.get("creatorUserId"),
                            "updated": t.get("updated"),
                            "updaterUserId": t.get("updaterUserId"),
                        })
                    parsed_data = {"trackers": trackers}
                    return ToolResult(success=True, output=response.text, data=parsed_data)
                else:
                    error = response.text
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            error = errors[0].get("message", error)
                        else:
                            error = error_data.get("message", error)
                    except ValueError:
                        pass
                    return ToolResult(success=False, output="", error=error)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")