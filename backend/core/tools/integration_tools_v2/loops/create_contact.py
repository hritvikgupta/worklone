from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LoopsCreateContactTool(BaseTool):
    name = "loops_create_contact"
    description = "Create a new contact in your Loops audience with an email address and optional properties like name, user group, and mailing list subscriptions."
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

    def _build_body(self, parameters: dict) -> dict[str, Any]:
        body: dict[str, Any] = {}
        custom_props = parameters.get("customProperties")
        if custom_props:
            if isinstance(custom_props, str):
                custom_props = json.loads(custom_props)
            body.update(custom_props)
        body["email"] = parameters["email"].strip()
        for field in ["firstName", "lastName", "source", "userGroup", "userId"]:
            val = parameters.get(field)
            if val:
                body[field] = str(val).strip()
        subscribed = parameters.get("subscribed")
        if subscribed is not None:
            body["subscribed"] = bool(subscribed)
        mailing_lists = parameters.get("mailingLists")
        if mailing_lists:
            if isinstance(mailing_lists, str):
                mailing_lists = json.loads(mailing_lists)
            body["mailingLists"] = mailing_lists
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The email address for the new contact",
                },
                "firstName": {
                    "type": "string",
                    "description": "The contact first name",
                },
                "lastName": {
                    "type": "string",
                    "description": "The contact last name",
                },
                "source": {
                    "type": "string",
                    "description": 'Custom source value replacing the default "API"',
                },
                "subscribed": {
                    "type": "boolean",
                    "description": "Whether the contact receives campaign emails (defaults to true)",
                },
                "userGroup": {
                    "type": "string",
                    "description": "Group to segment the contact into (one group per contact)",
                },
                "userId": {
                    "type": "string",
                    "description": "Unique user identifier from your application",
                },
                "mailingLists": {
                    "type": "object",
                    "description": "Mailing list IDs mapped to boolean values (true to subscribe, false to unsubscribe)",
                },
                "customProperties": {
                    "type": "object",
                    "description": "Custom contact properties as key-value pairs (string, number, boolean, or date values)",
                },
            },
            "required": ["email"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("LOOPS_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = "https://app.loops.so/api/v1/contacts/create"
        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(success=False, output="", error="Invalid JSON response")

                if not data.get("success"):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("message", "Failed to create contact"),
                    )

                output_data = {"success": True, "id": data.get("id")}
                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")