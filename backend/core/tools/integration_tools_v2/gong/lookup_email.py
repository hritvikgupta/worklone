from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongLookupEmailTool(BaseTool):
    name = "gong_lookup_email"
    description = "Find all references to an email address in Gong (calls, email messages, meetings, CRM data, engagement)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKey",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="accessKeySecret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "emailAddress": {
                    "type": "string",
                    "description": "Email address to look up",
                },
            },
            "required": ["emailAddress"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("accessKey") if context else None
        access_key_secret = context.get("accessKeySecret") if context else None
        
        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong access credentials not configured.")
        
        auth_str = f"{access_key}:{access_key_secret}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}",
        }
        
        url = "https://api.gong.io/v2/data-privacy/data-for-email-address"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"emailAddress": parameters.get("emailAddress", "")},
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        data = response.json()
                        error_msg = data.get("errors", [{}])[0].get("message") or data.get("message") or response.text
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")