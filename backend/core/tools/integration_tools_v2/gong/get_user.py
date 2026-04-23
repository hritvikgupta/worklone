from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetUserTool(BaseTool):
    name = "Gong Get User"
    description = "Retrieve details for a specific user from Gong."
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
                "userId": {
                    "type": "string",
                    "description": "The Gong user ID to retrieve",
                },
            },
            "required": ["userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY") if context else None
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Access keys not configured.")

        auth_string = f"{access_key}:{access_key_secret}"
        auth_header = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        }

        user_id = parameters.get("userId")
        if not user_id:
            return ToolResult(success=False, output="", error="userId is required.")

        url = f"https://api.gong.io/v2/users/{user_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                try:
                    data = response.json()
                except ValueError:
                    if 200 <= response.status_code < 300:
                        return ToolResult(success=True, output=response.text, data={"raw": response.text})
                    else:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                if 200 <= response.status_code < 300:
                    user = data.get("user", data)
                    output_data = {
                        "id": user.get("id") or "",
                        "emailAddress": user.get("emailAddress"),
                        "created": user.get("created"),
                        "active": user.get("active", False),
                        "emailAliases": user.get("emailAliases", []),
                        "trustedEmailAddress": user.get("trustedEmailAddress"),
                        "firstName": user.get("firstName"),
                        "lastName": user.get("lastName"),
                        "title": user.get("title"),
                        "phoneNumber": user.get("phoneNumber"),
                        "extension": user.get("extension"),
                        "personalMeetingUrls": user.get("personalMeetingUrls", []),
                        "settings": user.get("settings"),
                        "managerId": user.get("managerId"),
                        "meetingConsentPageUrl": user.get("meetingConsentPageUrl"),
                        "spokenLanguages": user.get("spokenLanguages", []),
                    }
                    output_str = json.dumps(output_data, default=str)
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    error_msg = "Failed to get user"
                    errors = data.get("errors")
                    if errors and len(errors) > 0:
                        error_msg = errors[0].get("message", error_msg)
                    if error_msg == "Failed to get user":
                        error_msg = data.get("message", error_msg)
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")