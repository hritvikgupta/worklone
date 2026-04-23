from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyCreateNoteTool(BaseTool):
    name = "ashby_create_note"
    description = """Creates a note on a candidate in Ashby. Supports plain text and HTML content (bold, italic, underline, links, lists, code)."""
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ashby_api_key",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("ashby_api_key") if context else None
        if self._is_placeholder_token(api_key or ""):
            api_key = os.getenv("ASHBY_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to add the note to",
                },
                "note": {
                    "type": "string",
                    "description": "The note content. If noteType is text/html, supports: <b>, <i>, <u>, <a>, <ul>, <ol>, <li>, <code>, <pre>",
                },
                "noteType": {
                    "type": "string",
                    "description": "Content type of the note: text/plain (default) or text/html",
                },
                "sendNotifications": {
                    "type": "boolean",
                    "description": "Whether to send notifications to subscribed users (default false)",
                },
            },
            "required": ["candidateId", "note"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }

        url = "https://api.ashbyhq.com/candidate.createNote"

        body: Dict[str, Any] = {
            "candidateId": parameters["candidateId"],
            "sendNotifications": parameters.get("sendNotifications", False),
        }
        note_type = parameters.get("noteType")
        if note_type == "text/html":
            body["note"] = {
                "type": "text/html",
                "value": parameters["note"],
            }
        else:
            body["note"] = parameters["note"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    error_info = data.get("errorInfo", {})
                    error_msg = error_info.get("message", "Failed to create note")
                    return ToolResult(success=False, output="", error=error_msg)

                results = data.get("results", {})
                note_id = results.get("id")
                output_data = {"noteId": note_id}

                return ToolResult(
                    success=True,
                    output=f"Note created successfully with ID: {note_id}",
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")