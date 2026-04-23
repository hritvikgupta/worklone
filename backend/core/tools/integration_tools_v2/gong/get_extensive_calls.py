from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetExtensiveCallsTool(BaseTool):
    name = "gong_get_extensive_calls"
    description = "Retrieve detailed call data including trackers, topics, and highlights from Gong."
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
                "callIds": {
                    "type": "string",
                    "description": "Comma-separated list of call IDs to retrieve detailed data for",
                },
                "fromDateTime": {
                    "type": "string",
                    "description": "Start date/time filter in ISO-8601 format",
                },
                "toDateTime": {
                    "type": "string",
                    "description": "End date/time filter in ISO-8601 format",
                },
                "workspaceId": {
                    "type": "string",
                    "description": "Gong workspace ID to filter calls",
                },
                "primaryUserIds": {
                    "type": "string",
                    "description": "Comma-separated list of user IDs to filter calls by host",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        credentials = context.get("credentials", {}) if context else {}
        access_key = credentials.get("GONG_ACCESS_KEY") or os.getenv("GONG_ACCESS_KEY")
        access_key_secret = credentials.get("GONG_ACCESS_KEY_SECRET") or os.getenv("GONG_ACCESS_KEY_SECRET")

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access keys not configured.")

        auth_str = base64.b64encode(f"{access_key}:{access_key_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_str}",
        }

        filter_obj: Dict[str, Any] = {}
        call_ids = parameters.get("callIds", "")
        if call_ids:
            filter_obj["callIds"] = [cid.strip() for cid in call_ids.split(",")]
        from_dt = parameters.get("fromDateTime")
        if from_dt:
            filter_obj["fromDateTime"] = from_dt
        to_dt = parameters.get("toDateTime")
        if to_dt:
            filter_obj["toDateTime"] = to_dt
        ws_id = parameters.get("workspaceId")
        if ws_id:
            filter_obj["workspaceId"] = ws_id
        pu_ids = parameters.get("primaryUserIds", "")
        if pu_ids:
            filter_obj["primaryUserIds"] = [uid.strip() for uid in pu_ids.split(",")]

        body: Dict[str, Any] = {
            "filter": filter_obj,
            "contentSelector": {
                "exposedFields": {
                    "parties": True,
                    "content": {
                        "structure": True,
                        "topics": True,
                        "trackers": True,
                        "trackerOccurrences": True,
                        "highlights": True,
                    },
                    "collaboration": {"publicComments": True},
                    "interaction": {
                        "personInteractionStats": True,
                        "speakers": True,
                        "video": True,
                        "questions": True,
                    },
                    "media": True,
                },
            },
        }
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor

        url = "https://api.gong.io/v2/calls/extensive"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")