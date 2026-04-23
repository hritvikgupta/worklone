from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListNotesTool(BaseTool):
    name = "ashby_list_notes"
    description = "Lists all notes on a candidate with pagination support."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to list notes for",
                },
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page",
                },
            },
            "required": ["candidateId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ashby_api_key") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
        }
        
        body = {
            "candidateId": parameters["candidateId"],
        }
        if parameters.get("cursor"):
            body["cursor"] = parameters["cursor"]
        if parameters.get("perPage") is not None:
            body["limit"] = parameters["perPage"]
        
        url = "https://api.ashbyhq.com/candidate.listNotes"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if not data.get("success", False):
                    error_msg = (
                        data.get("errorInfo", {}).get("message", "Failed to list notes")
                        if isinstance(data, dict)
                        else response.text
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")