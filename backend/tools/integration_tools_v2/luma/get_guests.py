from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaGetGuestsTool(BaseTool):
    name = "luma_get_guests"
    description = "Retrieve the guest list for a Luma event with optional filtering by approval status, sorting, and pagination."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "eventId": {
                    "type": "string",
                    "description": "Event ID (starts with evt-)",
                },
                "approvalStatus": {
                    "type": "string",
                    "description": "Filter by approval status: approved, session, pending_approval, invited, declined, or waitlist",
                },
                "paginationLimit": {
                    "type": "number",
                    "description": "Maximum number of guests to return per page",
                },
                "paginationCursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response (next_cursor) to fetch the next page of results",
                },
                "sortColumn": {
                    "type": "string",
                    "description": "Column to sort by: name, email, created_at, registered_at, or checked_in_at",
                },
                "sortDirection": {
                    "type": "string",
                    "description": "Sort direction: asc, desc, asc nulls last, or desc nulls last",
                },
            },
            "required": ["eventId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("LUMA_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Luma API key not configured.")

        headers = {
            "x-luma-api-key": api_key,
            "Accept": "application/json",
        }

        params: Dict[str, Any] = {
            "event_id": (parameters.get("eventId") or "").strip(),
        }
        if parameters.get("approvalStatus"):
            params["approval_status"] = parameters["approvalStatus"]
        if parameters.get("paginationLimit") is not None:
            params["pagination_limit"] = parameters["paginationLimit"]
        if parameters.get("paginationCursor"):
            params["pagination_cursor"] = parameters["paginationCursor"]
        if parameters.get("sortColumn"):
            params["sort_column"] = parameters["sortColumn"]
        if parameters.get("sortDirection"):
            params["sort_direction"] = parameters["sortDirection"]

        url = "https://public-api.luma.com/v1/event/get-guests"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    guests = []
                    for entry in data.get("entries", []):
                        guest = entry.get("guest", {}) if isinstance(entry, dict) else {}
                        guests.append({
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
                        })
                    transformed = {
                        "guests": guests,
                        "hasMore": data.get("has_more", False),
                        "nextCursor": data.get("next_cursor"),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed),
                        data=transformed,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=response.text,
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")