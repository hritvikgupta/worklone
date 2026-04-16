import httpx
import json
import os
from typing import Any, Dict
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaAddGuestsTool(BaseTool):
    name = "luma_add_guests"
    description = "Add guests to a Luma event by email. Guests are added with Going (approved) status and receive one ticket of the default ticket type."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LUMA_API_KEY",
                description="Luma API key",
                env_var="LUMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        api_key = context.get("LUMA_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("LUMA_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            raise ValueError("Luma API key not configured.")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "eventId": {
                    "type": "string",
                    "description": "Event ID (starts with evt-)",
                },
                "guests": {
                    "type": "string",
                    "description": 'JSON array of guest objects. Each guest requires an "email" field and optionally "name", "first_name", "last_name". Example: [{"email": "user@example.com", "name": "John Doe"}]',
                },
            },
            "required": ["eventId", "guests"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        try:
            api_key = self._get_api_key(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        headers = {
            "x-luma-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = "https://public-api.luma.com/v1/event/add-guests"

        event_id = parameters["eventId"].strip()
        guests_param = parameters["guests"]
        try:
            guests_array = json.loads(guests_param)
        except (json.JSONDecodeError, TypeError):
            guests_array = [{"email": guests_param}]

        body = {
            "event_id": event_id,
            "guests": guests_array,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if not response.is_success:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message") or error_data.get("error") or response.text or "Failed to add guests"
                    except:
                        error_msg = response.text or "Failed to add guests"
                    return ToolResult(success=False, output="", error=error_msg)

                try:
                    data = response.json()
                except:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                entries = data.get("entries", [])
                guests = []
                for entry in entries:
                    guest = entry.get("guest", {})
                    g = {
                        "id": guest.get("id"),
                        "email": guest.get("user_email"),
                        "name": guest.get("user_name"),
                        "firstName": guest.get("user_first_name"),
                        "lastName": guest.get("user_last_name"),
                        "approvalStatus": guest.get("approval_status"),
                        "registeredAt": guest.get("registered_at"),
                        "invitedAt": guest.get("invited_at"),
                        "joinedAt": guest.get("joined_at"),
                        "checkedInAt": guest.get("checked_in_at"),
                        "phoneNumber": guest.get("phone_number"),
                    }
                    guests.append(g)

                result_data = {"guests": guests}
                return ToolResult(success=True, output=json.dumps(result_data), data=result_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")