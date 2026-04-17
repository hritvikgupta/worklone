from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceDeleteOpportunityTool(BaseTool):
    name = "salesforce_delete_opportunity"
    description = "Delete an opportunity"
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

    def _get_instance_url(self, id_token: str | None, instance_url: str | None) -> str:
        if instance_url and instance_url.strip():
            return instance_url.rstrip("/")
        if not id_token:
            raise ValueError("Either instanceUrl or idToken must be provided.")
        try:
            parts = id_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format.")
            payload = parts[1]
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += "=" * (4 - missing_padding)
            decoded_payload = base64.urlsafe_b64decode(payload)
            payload_dict = json.loads(decoded_payload.decode("utf-8"))
            iss = payload_dict.get("iss")
            if not iss:
                raise ValueError("No 'iss' claim in id_token.")
            return iss.rstrip("/")
        except Exception as e:
            raise ValueError(f"Failed to extract instance URL from idToken: {str(e)}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "opportunityId": {
                    "type": "string",
                    "description": "Salesforce Opportunity ID to delete (18-character string starting with 006)",
                },
            },
            "required": ["opportunityId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        id_token = context.get("idToken") if context else None
        instance_url_param = context.get("instanceUrl") if context else None
        try:
            instance_url = self._get_instance_url(id_token, instance_url_param)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        opportunity_id = parameters.get("opportunityId")
        if not opportunity_id:
            return ToolResult(success=False, output="", error="opportunityId is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        url = f"{instance_url}/services/data/v59.0/sobjects/Opportunity/{opportunity_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"id": opportunity_id, "deleted": True},
                    )
                else:
                    try:
                        data = response.json()
                        if isinstance(data, list) and data:
                            error_msg = data[0].get("message", str(data[0]))
                        else:
                            error_msg = data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")