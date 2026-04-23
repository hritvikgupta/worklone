from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LoopsCreateContactPropertyTool(BaseTool):
    name = "loops_create_contact_property"
    description = "Create a new custom contact property in your Loops account. The property name must be in camelCase format."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LOOPS_API_KEY",
                description="Loops API key for authentication",
                env_var="LOOPS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The property name in camelCase format (e.g., \"favoriteColor\")",
                },
                "type": {
                    "type": "string",
                    "description": "The property data type (e.g., \"string\", \"number\", \"boolean\", \"date\")",
                },
            },
            "required": ["name", "type"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        credentials = context.get("credentials", {}) if context else {}
        api_key = credentials.get("LOOPS_API_KEY")

        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Loops API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "name": parameters["name"],
            "type": parameters["type"],
        }

        url = "https://app.loops.so/api/v1/contacts/properties"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("message", "Failed to create contact property"),
                    )

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")