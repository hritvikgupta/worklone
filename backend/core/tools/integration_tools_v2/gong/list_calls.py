from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListCallsTool(BaseTool):
    name = "gong_list_calls"
    description = "Retrieve call data by date range from Gong."
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
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fromDateTime": {
                    "type": "string",
                    "description": "Start date/time in ISO-8601 format (e.g., 2024-01-01T00:00:00Z)",
                },
                "toDateTime": {
                    "type": "string",
                    "description": "End date/time in ISO-8601 format (e.g., 2024-01-31T23:59:59Z). If omitted, lists calls up to the most recent.",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
                "workspaceId": {
                    "type": "string",
                    "description": "Gong workspace ID to filter calls",
                },
            },
            "required": ["fromDateTime"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        gong_access_key = context.get("gong_access_key") if context else None
        gong_access_key_secret = context.get("gong_access_key_secret") if context else None

        if self._is_placeholder_token(gong_access_key or "") or self._is_placeholder_token(gong_access_key_secret or ""):
            return ToolResult(success=False, output="", error="Access credentials not configured.")

        credentials = f"{gong_access_key}:{gong_access_key_secret}"
        auth_header = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        }

        url = "https://api.gong.io/v2/calls"
        params_dict = {
            "fromDateTime": parameters["fromDateTime"],
        }
        optional_params = ["toDateTime", "cursor", "workspaceId"]
        for param_key in optional_params:
            if param_key in parameters:
                params_dict[param_key] = parameters[param_key]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    resp_data = response.json()
                    raw_calls = resp_data.get("calls", [])
                    calls = []
                    for call in raw_calls:
                        calls.append({
                            "id": call.get("id", ""),
                            "title": call.get("title"),
                            "scheduled": call.get("scheduled"),
                            "started": call.get("started", ""),
                            "duration": call.get("duration", 0),
                            "direction": call.get("direction"),
                            "system": call.get("system"),
                            "scope": call.get("scope"),
                            "media": call.get("media"),
                            "language": call.get("language"),
                            "url": call.get("url"),
                            "primaryUserId": call.get("primaryUserId"),
                            "workspaceId": call.get("workspaceId"),
                            "sdrDisposition": call.get("sdrDisposition"),
                            "clientUniqueId": call.get("clientUniqueId"),
                            "customData": call.get("customData"),
                            "purpose": call.get("purpose"),
                            "meetingUrl": call.get("meetingUrl"),
                            "isPrivate": call.get("isPrivate", False),
                            "calendarEventId": call.get("calendarEventId"),
                        })
                    records = resp_data.get("records", {})
                    output_data = {
                        "calls": calls,
                        "cursor": records.get("cursor"),
                        "totalRecords": records.get("totalRecords", len(calls)),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    error_text = response.text
                    error_msg = error_text
                    try:
                        data = response.json()
                        errors = data.get("errors", [])
                        if errors:
                            error_msg = errors[0].get("message", "")
                        elif data.get("message"):
                            error_msg = data["message"]
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")