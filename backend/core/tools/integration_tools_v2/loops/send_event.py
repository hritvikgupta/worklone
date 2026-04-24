from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LoopsSendEventTool(BaseTool):
    name = "loops_send_event"
    description = "Send an event to Loops to trigger automated email sequences for a contact. Identify the contact by email or userId and include optional event properties and mailing list changes."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="loops_api_key",
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
                "email": {
                    "type": "string",
                    "description": "The email address of the contact (at least one of email or userId is required)",
                },
                "userId": {
                    "type": "string",
                    "description": "The userId of the contact (at least one of email or userId is required)",
                },
                "eventName": {
                    "type": "string",
                    "description": "The name of the event to trigger",
                },
                "eventProperties": {
                    "type": "object",
                    "description": "Event data as key-value pairs (string, number, boolean, or date values)",
                },
                "mailingLists": {
                    "type": "object",
                    "description": "Mailing list IDs mapped to boolean values (true to subscribe, false to unsubscribe)",
                },
            },
            "required": ["eventName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("loops_api_key") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Loops API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        email = parameters.get("email")
        user_id = parameters.get("userId")
        if not email and not user_id:
            return ToolResult(success=False, output="", error="At least one of email or userId is required to send an event")

        body: Dict[str, Any] = {
            "eventName": parameters["eventName"],
        }

        if email:
            body["email"] = email.strip()
        if user_id:
            body["userId"] = user_id.strip()

        event_properties = parameters.get("eventProperties")
        if event_properties:
            if isinstance(event_properties, str):
                body["eventProperties"] = json.loads(event_properties)
            else:
                body["eventProperties"] = event_properties

        mailing_lists = parameters.get("mailingLists")
        if mailing_lists:
            if isinstance(mailing_lists, str):
                body["mailingLists"] = json.loads(mailing_lists)
            else:
                body["mailingLists"] = mailing_lists

        url = "https://app.loops.so/api/v1/events/send"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                    if isinstance(data, dict) and data.get("success"):
                        return ToolResult(
                            success=True,
                            output=json.dumps({"success": True}),
                            data=data,
                        )
                    else:
                        error_msg = data.get("message") if isinstance(data, dict) else "Failed to send event"
                        return ToolResult(success=False, output="", error=error_msg)
                except Exception:
                    return ToolResult(success=True, output=response.text, data={})

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")