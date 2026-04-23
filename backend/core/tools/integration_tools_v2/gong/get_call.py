from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetCallTool(BaseTool):
    name = "Gong Get Call"
    description = "Retrieve detailed data for a specific call from Gong."
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
                "callId": {
                    "type": "string",
                    "description": "The Gong call ID to retrieve",
                },
            },
            "required": ["callId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY", "") if context else ""
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET", "") if context else ""

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong API credentials not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_key}:{access_key_secret}'.encode('utf-8')).decode('utf-8')}",
        }

        call_id = parameters["callId"]
        url = f"https://api.gong.io/v2/calls/{call_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    call = data.get("call", data)
                    output = {
                        "id": call.get("id") or "",
                        "title": call.get("title"),
                        "url": call.get("url"),
                        "scheduled": call.get("scheduled"),
                        "started": call.get("started") or "",
                        "duration": call.get("duration", 0),
                        "direction": call.get("direction"),
                        "system": call.get("system"),
                        "scope": call.get("scope"),
                        "media": call.get("media"),
                        "language": call.get("language"),
                        "primaryUserId": call.get("primaryUserId"),
                        "workspaceId": call.get("workspaceId"),
                        "sdrDisposition": call.get("sdrDisposition"),
                        "clientUniqueId": call.get("clientUniqueId"),
                        "customData": call.get("customData"),
                        "purpose": call.get("purpose"),
                        "meetingUrl": call.get("meetingUrl"),
                        "isPrivate": call.get("isPrivate", False),
                        "calendarEventId": call.get("calendarEventId"),
                    }
                    return ToolResult(success=True, output=json.dumps(output), data=output)
                else:
                    error = "Failed to get call"
                    try:
                        err_data = response.json()
                        errors = err_data.get("errors", [])
                        if errors:
                            error = errors[0].get("message", error)
                        elif err_data.get("message"):
                            error = err_data["message"]
                        else:
                            error = response.text
                    except Exception:
                        error = response.text
                    return ToolResult(success=False, output="", error=error)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")