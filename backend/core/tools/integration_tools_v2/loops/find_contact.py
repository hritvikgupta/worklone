from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LoopsFindContactTool(BaseTool):
    name = "loops_find_contact"
    description = "Find a contact in Loops by email address or userId. Returns an array of matching contacts with all their properties including name, subscription status, user group, and mailing lists."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "loops",
            context=context,
            context_token_keys=("loops_api_key",),
            env_token_keys=("LOOPS_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The contact email address to search for (at least one of email or userId is required)",
                },
                "userId": {
                    "type": "string",
                    "description": "The contact userId to search for (at least one of email or userId is required)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        email = (parameters.get("email") or "").strip()
        user_id = (parameters.get("userId") or "").strip()
        if not email and not user_id:
            return ToolResult(success=False, output="", error="At least one of email or userId is required to find a contact")
        
        base_url = "https://app.loops.so/api/v1/contacts/find"
        if email:
            url = f"{base_url}?email={urllib.parse.quote(email)}"
        else:
            url = f"{base_url}?userId={urllib.parse.quote(user_id)}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if isinstance(data, list):
                        contacts = []
                        for contact_raw in data:
                            if isinstance(contact_raw, dict):
                                contact = {
                                    "id": contact_raw.get("id") or "",
                                    "email": contact_raw.get("email") or "",
                                    "firstName": contact_raw.get("firstName"),
                                    "lastName": contact_raw.get("lastName"),
                                    "source": contact_raw.get("source"),
                                    "subscribed": contact_raw.get("subscribed", False),
                                    "userGroup": contact_raw.get("userGroup"),
                                    "userId": contact_raw.get("userId"),
                                    "mailingLists": contact_raw.get("mailingLists", {}),
                                    "optInStatus": contact_raw.get("optInStatus"),
                                }
                                contacts.append(contact)
                        result_data = {"contacts": contacts}
                        return ToolResult(success=True, output=json.dumps(result_data), data=result_data)
                    else:
                        error_msg = data.get("message") if isinstance(data, dict) else "Failed to find contact"
                        return ToolResult(success=False, output="", error=error_msg)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")