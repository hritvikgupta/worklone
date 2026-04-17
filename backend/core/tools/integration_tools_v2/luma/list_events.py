from typing import Any, Dict, List, Optional
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaListEventsTool(BaseTool):
    name = "luma_list_events"
    description = "List events from your Luma calendar with optional date range filtering, sorting, and pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="luma_api_key",
                description="Luma API key",
                env_var="LUMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> Optional[str]:
        api_key = context.get("luma_api_key") if context else None
        if self._is_placeholder_token(api_key or ""):
            return None
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "after": {
                    "type": "string",
                    "description": "Return events after this ISO 8601 datetime (e.g., 2025-01-01T00:00:00Z)",
                },
                "before": {
                    "type": "string",
                    "description": "Return events before this ISO 8601 datetime (e.g., 2025-12-31T23:59:59Z)",
                },
                "paginationLimit": {
                    "type": "number",
                    "description": "Maximum number of events to return per page",
                },
                "paginationCursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response (next_cursor) to fetch the next page of results",
                },
                "sortColumn": {
                    "type": "string",
                    "description": "Column to sort by (only start_at is supported)",
                },
                "sortDirection": {
                    "type": "string",
                    "description": "Sort direction: asc, desc, asc nulls last, or desc nulls last",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        if not api_key:
            return ToolResult(success=False, output="", error="Luma API key not configured.")

        headers = {
            "x-luma-api-key": api_key,
            "Accept": "application/json",
        }

        query_params: Dict[str, str] = {}
        if parameters.get("after"):
            query_params["after"] = parameters["after"]
        if parameters.get("before"):
            query_params["before"] = parameters["before"]
        if parameters.get("paginationLimit") is not None:
            query_params["pagination_limit"] = str(parameters["paginationLimit"])
        if parameters.get("paginationCursor"):
            query_params["pagination_cursor"] = parameters["paginationCursor"]
        if parameters.get("sortColumn"):
            query_params["sort_column"] = parameters["sortColumn"]
        if parameters.get("sortDirection"):
            query_params["sort_direction"] = parameters["sortDirection"]

        url = "https://public-api.luma.com/v1/calendar/list-events"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    entries = data.get("entries", [])
                    events = []
                    for entry in entries:
                        event = entry.get("event", {}) if isinstance(entry, dict) else {}
                        events.append({
                            "id": event.get("id"),
                            "name": event.get("name"),
                            "startAt": event.get("start_at"),
                            "endAt": event.get("end_at"),
                            "timezone": event.get("timezone"),
                            "durationInterval": event.get("duration_interval"),
                            "createdAt": event.get("created_at"),
                            "description": event.get("description"),
                            "descriptionMd": event.get("description_md"),
                            "coverUrl": event.get("cover_url"),
                            "url": event.get("url"),
                            "visibility": event.get("visibility"),
                            "meetingUrl": event.get("meeting_url"),
                            "geoAddressJson": event.get("geo_address_json"),
                            "geoLatitude": event.get("geo_latitude"),
                            "geoLongitude": event.get("geo_longitude"),
                            "calendarId": event.get("calendar_id"),
                        })
                    transformed = {
                        "events": events,
                        "hasMore": data.get("has_more", False),
                        "nextCursor": data.get("next_cursor"),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message") or err_data.get("error") or error_msg
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")