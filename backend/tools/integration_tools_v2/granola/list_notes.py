from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GranolaListNotesTool(BaseTool):
    name = "granola_list_notes"
    description = "Lists meeting notes from Granola with optional date filters and pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="Granola API key",
                env_var="GRANOLA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        return (context.get("api_key") or "") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "createdBefore": {
                    "type": "string",
                    "description": "Return notes created before this date (ISO 8601)",
                },
                "createdAfter": {
                    "type": "string",
                    "description": "Return notes created after this date (ISO 8601)",
                },
                "updatedAfter": {
                    "type": "string",
                    "description": "Return notes updated after this date (ISO 8601)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of notes per page (1-30, default 10)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Granola API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = "https://public-api.granola.ai/v1/notes"
        params = {}
        for param_key, api_key in [
            ("created_before", parameters.get("createdBefore")),
            ("created_after", parameters.get("createdAfter")),
            ("updated_after", parameters.get("updatedAfter")),
            ("cursor", parameters.get("cursor")),
            ("page_size", parameters.get("pageSize")),
        ]:
            if param_key is not None:
                params[api_key] = param_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    notes = data.get("notes", [])
                    transformed_notes = []
                    for note in notes:
                        owner = note.get("owner", {})
                        transformed_notes.append({
                            "id": note.get("id"),
                            "title": note.get("title"),
                            "ownerName": owner.get("name"),
                            "ownerEmail": owner.get("email", ""),
                            "createdAt": note.get("created_at", ""),
                            "updatedAt": note.get("updated_at", ""),
                        })
                    output_data = {
                        "notes": transformed_notes,
                        "hasMore": data.get("hasMore", False),
                        "cursor": data.get("cursor"),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Granola API error ({response.status_code}): {response.text}",
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")