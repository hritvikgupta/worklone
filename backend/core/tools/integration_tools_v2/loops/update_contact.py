from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LoopsUpdateContactTool(BaseTool):
    name = "Loops Update Contact"
    description = """Update an existing contact in Loops by email or userId. Creates a new contact if no match is found (upsert). Can update name, subscription status, user group, mailing lists, and custom properties."""
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
                "email": {
                    "type": "string",
                    "description": "The contact email address (at least one of email or userId is required)",
                },
                "userId": {
                    "type": "string",
                    "description": "The contact userId (at least one of email or userId is required)",
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
                    "description": "Whether the contact receives campaign emails (sending true re-subscribes unsubscribed contacts)",
                },
                "userGroup": {
                    "type": "string",
                    "description": "Group to segment the contact into (one group per contact)",
                },
                "mailingLists": {
                    "type": "object",
                    "additionalProperties": {"type": "boolean"},
                    "description": "Mailing list IDs mapped to boolean values (true to subscribe, false to unsubscribe)",
                },
                "customProperties": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Custom contact properties as key-value pairs (send null to reset a property)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("LOOPS_API_KEY") if context else None
        if self._is_placeholder_token(str(api_key or "")):
            return ToolResult(success=False, output="", error="API key not configured.")

        if not parameters.get("email") and not parameters.get("userId"):
            return ToolResult(success=False, output="", error="At least one of email or userId is required to update a contact")

        body: Dict[str, Any] = {}
        custom_props = parameters.get("customProperties")
        if custom_props:
            body.update(custom_props)

        email = parameters.get("email")
        if email:
            body["email"] = str(email).strip()
        user_id = parameters.get("userId")
        if user_id:
            body["userId"] = str(user_id).strip()
        first_name = parameters.get("firstName")
        if first_name:
            body["firstName"] = str(first_name).strip()
        last_name = parameters.get("lastName")
        if last_name:
            body["lastName"] = str(last_name).strip()
        source = parameters.get("source")
        if source:
            body["source"] = str(source).strip()
        subscribed = parameters.get("subscribed")
        if subscribed is not None:
            body["subscribed"] = subscribed
        user_group = parameters.get("userGroup")
        if user_group:
            body["userGroup"] = str(user_group).strip()
        mailing_lists = parameters.get("mailingLists")
        if mailing_lists:
            body["mailingLists"] = mailing_lists

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = "https://app.loops.so/api/v1/contacts/update"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if data.get("success"):
                            return ToolResult(success=True, output=response.text, data=data)
                        else:
                            return ToolResult(
                                success=False,
                                output="",
                                error=data.get("message") or "Failed to update contact",
                            )
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")