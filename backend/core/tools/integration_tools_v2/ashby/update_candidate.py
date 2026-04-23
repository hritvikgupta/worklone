from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyUpdateCandidateTool(BaseTool):
    name = "ashby_update_candidate"
    description = "Updates an existing candidate record in Ashby. Only provided fields are changed."
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
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated full name",
                },
                "email": {
                    "type": "string",
                    "description": "Updated primary email address",
                },
                "phoneNumber": {
                    "type": "string",
                    "description": "Updated primary phone number",
                },
                "linkedInUrl": {
                    "type": "string",
                    "description": "LinkedIn profile URL",
                },
                "githubUrl": {
                    "type": "string",
                    "description": "GitHub profile URL",
                },
                "websiteUrl": {
                    "type": "string",
                    "description": "Personal website URL",
                },
                "sourceId": {
                    "type": "string",
                    "description": "UUID of the source to attribute the candidate to",
                },
            },
            "required": ["candidateId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("ASHBY_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        body: Dict[str, Any] = {
            "candidateId": parameters["candidateId"],
        }
        for field in [
            "name",
            "email",
            "phoneNumber",
            "linkedInUrl",
            "githubUrl",
            "websiteUrl",
            "sourceId",
        ]:
            if parameters.get(field):
                body[field] = parameters[field]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
        }

        url = "https://api.ashbyhq.com/candidate.update"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    data = {}

                if not data.get("success", False):
                    error_info = data.get("errorInfo", {})
                    error_msg = (
                        error_info.get("message") if isinstance(error_info, dict) else str(error_info)
                    ) or "Failed to update candidate"
                    return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")