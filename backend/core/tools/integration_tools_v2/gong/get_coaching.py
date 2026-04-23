from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetCoachingTool(BaseTool):
    name = "gong_get_coaching"
    description = "Retrieve coaching metrics for a manager from Gong."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="gong_access_key",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="gong_access_key_secret",
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
                "managerId": {
                    "type": "string",
                    "description": "Gong user ID of the manager",
                },
                "workspaceId": {
                    "type": "string",
                    "description": "Gong workspace ID",
                },
                "fromDate": {
                    "type": "string",
                    "description": "Start date in ISO-8601 format",
                },
                "toDate": {
                    "type": "string",
                    "description": "End date in ISO-8601 format",
                },
            },
            "required": ["managerId", "workspaceId", "fromDate", "toDate"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("gong_access_key") if context else None
        access_key_secret = context.get("gong_access_key_secret") if context else None

        if not access_key or not access_key_secret:
            return ToolResult(success=False, output="", error="Access credentials not configured.")

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Access credentials not configured.")

        credentials = base64.b64encode(f"{access_key}:{access_key_secret}".encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
        }

        url = "https://api.gong.io/v2/coaching"
        query_params = {
            "manager-id": parameters["managerId"],
            "workspace-id": parameters["workspaceId"],
            "from": parameters["fromDate"],
            "to": parameters["toDate"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("errors", [{}])[0].get("message")
                            or error_data.get("message")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")