from typing import Any, Dict, Optional
import httpx
import base64
import json
import re
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceDeleteAccountTool(BaseTool):
    name = "salesforce_delete_account"
    description = "Delete an account from Salesforce CRM"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _decode_id_token_instance_url(self, id_token: str) -> Optional[str]:
        try:
            base64_url = id_token.split(".")[1]
            base64_encoded = base64_url.replace("-", "+").replace("_", "/")
            base64_encoded += "=" * ((4 - len(base64_encoded) % 4) % 4)
            decoded_bytes = base64.b64decode(base64_encoded)
            decoded_str = decoded_bytes.decode("utf-8")
            decoded = json.loads(decoded_str)
            profile = decoded.get("profile")
            if profile:
                match = re.match(r"^(https://[^/]+)", profile)
                if match:
                    return match.group(1)
            sub = decoded.get("sub")
            if sub:
                match = re.match(r"^(https://[^/]+)", sub)
                if match and match.group(1) != "https://login.salesforce.com":
                    return match.group(1)
        except Exception:
            pass
        return None

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accountId": {
                    "type": "string",
                    "description": "Salesforce Account ID to delete (18-character string starting with 001)",
                }
            },
            "required": ["accountId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        account_id = parameters.get("accountId")
        if not account_id:
            return ToolResult(success=False, output="", error="Account ID is required.")

        id_token = context.get("idToken") if context else None
        instance_url = context.get("instanceUrl") if context else None

        if not instance_url and id_token:
            instance_url = self._decode_id_token_instance_url(id_token)

        if not instance_url:
            return ToolResult(success=False, output="", error="Salesforce instance URL is required but not provided.")

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Account/{account_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output=response.text,
                        data={"id": account_id, "deleted": True},
                    )
                else:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {}
                    if isinstance(error_data, list) and error_data:
                        error_msg = error_data[0].get("message", "Failed to delete account from Salesforce")
                    else:
                        error_msg = error_data.get("message", "Failed to delete account from Salesforce")
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")