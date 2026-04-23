from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioEscalationsCreateTool(BaseTool):
    name = "incidentio_escalations_create"
    description = "Create a new escalation policy in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_API_KEY",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("INCIDENTIO_API_KEY") if context else None
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "idempotency_key": {
                    "type": "string",
                    "description": "Unique identifier to prevent duplicate escalation creation. Use a UUID or unique string.",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the escalation (e.g., \"Database Critical Alert\")",
                },
                "escalation_path_id": {
                    "type": "string",
                    "description": "ID of the escalation path to use (required if user_ids not provided)",
                },
                "user_ids": {
                    "type": "string",
                    "description": "Comma-separated list of user IDs to notify (required if escalation_path_id not provided)",
                },
            },
            "required": ["idempotency_key", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.incident.io/v2/escalations"
        
        body = {
            "idempotency_key": parameters["idempotency_key"],
            "title": parameters["title"],
        }
        
        if parameters.get("escalation_path_id"):
            body["escalation_path_id"] = parameters["escalation_path_id"]
        
        if parameters.get("user_ids"):
            body["user_ids"] = [user_id.strip() for user_id in parameters["user_ids"].split(",")]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")