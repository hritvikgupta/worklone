from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyRemoveCandidateTagTool(BaseTool):
    name = "ashby_remove_candidate_tag"
    description = "Removes a tag from a candidate in Ashby."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("ashby_api_key") if context else None
        if api_key is None:
            api_key = os.getenv("ASHBY_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to remove the tag from",
                },
                "tagId": {
                    "type": "string",
                    "description": "The UUID of the tag to remove",
                },
            },
            "required": ["candidateId", "tagId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/candidate.removeTag"
        body = {
            "candidateId": parameters["candidateId"],
            "tagId": parameters["tagId"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if data.get("success"):
                            return ToolResult(success=True, output='{"success": true}', data=data)
                        else:
                            error_msg = data.get("errorInfo", {}).get("message", "Failed to remove tag from candidate")
                            return ToolResult(success=False, output="", error=error_msg)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")