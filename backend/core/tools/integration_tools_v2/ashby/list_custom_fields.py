from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListCustomFieldsTool(BaseTool):
    name = "ashby_list_custom_fields"
    description = "Lists all custom field definitions configured in Ashby."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ASHBY_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }

        url = "https://api.ashbyhq.com/customField.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error=response.text)

                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list custom fields")
                    return ToolResult(success=False, output="", error=error_msg)

                custom_fields = [
                    {
                        "id": f.get("id"),
                        "title": f.get("title"),
                        "fieldType": f.get("fieldType"),
                        "objectType": f.get("objectType"),
                        "isArchived": f.get("isArchived", False),
                    }
                    for f in data.get("results", [])
                ]
                output_data = {"customFields": custom_fields}
                output_str = json.dumps(output_data)

                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")