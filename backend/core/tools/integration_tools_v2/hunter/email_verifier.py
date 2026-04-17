from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterEmailVerifierTool(BaseTool):
    name = "hunter_email_verifier"
    description = "Verifies the deliverability of an email address and provides detailed verification status."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUNTER_API_KEY",
                description="Hunter.io API Key",
                env_var="HUNTER_API_KEY",
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
                    "description": "The email address to verify",
                }
            },
            "required": ["email"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (context or {}).get("HUNTER_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Hunter API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://api.hunter.io/v2/email-verifier"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={
                        "email": parameters["email"],
                        "api_key": api_key,
                    },
                )

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    transformed = {
                        "result": data.get("data", {}).get("result", "unknown"),
                        "score": data.get("data", {}).get("score", 0),
                        "email": data.get("data", {}).get("email", ""),
                        "regexp": data.get("data", {}).get("regexp", False),
                        "gibberish": data.get("data", {}).get("gibberish", False),
                        "disposable": data.get("data", {}).get("disposable", False),
                        "webmail": data.get("data", {}).get("webmail", False),
                        "mx_records": data.get("data", {}).get("mx_records", False),
                        "smtp_server": data.get("data", {}).get("smtp_server", False),
                        "smtp_check": data.get("data", {}).get("smtp_check", False),
                        "accept_all": data.get("data", {}).get("accept_all", False),
                        "block": data.get("data", {}).get("block", False),
                        "status": data.get("data", {}).get("status", "unknown"),
                        "sources": data.get("data", {}).get("sources", []),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")