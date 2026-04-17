from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceDeleteCaseTool(BaseTool):
    name = "salesforce_delete_case"
    description = "Delete a case"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "caseId": {
                    "type": "string",
                    "description": "Salesforce Case ID to delete (18-character string starting with 500)",
                },
            },
            "required": ["caseId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        instance_url = getattr(connection, "instance_url", context.get("instanceUrl") if context else None)
        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        case_id = parameters["caseId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Case/{case_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = {
                        "id": case_id,
                        "deleted": True,
                    }
                    return ToolResult(success=True, output=json.dumps(data), data=data)
                else:
                    try:
                        error_data = response.json()
                    except:
                        error_data = {}
                    if isinstance(error_data, list) and len(error_data) > 0:
                        error_msg = error_data[0].get("message", str(error_data[0]))
                    elif isinstance(error_data, dict):
                        error_msg = error_data.get("message", response.text)
                    else:
                        error_msg = response.text
                    if not error_msg:
                        error_msg = "Failed to delete case"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")