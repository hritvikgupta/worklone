from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloSequenceAddContactsTool(BaseTool):
    name = "apollo_sequence_add_contacts"
    description = "Add contacts to an Apollo sequence"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key (master key required)",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        api_key = context.get("APOLLO_API_KEY", "")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sequence_id": {
                    "type": "string",
                    "description": "ID of the sequence to add contacts to (e.g., \"seq_abc123\")",
                },
                "contact_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of contact IDs to add to the sequence (e.g., [\"con_abc123\", \"con_def456\"])",
                },
                "emailer_campaign_id": {
                    "type": "string",
                    "description": "Optional emailer campaign ID",
                },
                "send_email_from_user_id": {
                    "type": "string",
                    "description": "User ID to send emails from",
                },
            },
            "required": ["sequence_id", "contact_ids"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        sequence_id = parameters["sequence_id"]
        url = f"https://api.apollo.io/api/v1/emailer_campaigns/{sequence_id}/add_contact_ids"
        
        body = {
            "contact_ids": parameters["contact_ids"],
        }
        optional_fields = ["emailer_campaign_id", "send_email_from_user_id"]
        for field in optional_fields:
            if field in parameters and parameters[field]:
                body[field] = parameters[field]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")