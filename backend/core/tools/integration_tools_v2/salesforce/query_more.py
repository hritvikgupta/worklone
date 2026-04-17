from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceQueryMoreTool(BaseTool):
    name = "salesforce_query_more"
    description = "Retrieve additional query results using the nextRecordsUrl from a previous query"
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

    async def _resolve_connection(self, context: dict | None) -> tuple[str, str | None]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", context.get("instanceUrl") if context else None)
        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accessToken": {"type": "string"},
                "idToken": {"type": "string"},
                "instanceUrl": {"type": "string"},
                "nextRecordsUrl": {
                    "type": "string",
                    "description": "The nextRecordsUrl value from a previous query response (e.g., /services/data/v59.0/query/01g...)",
                },
            },
            "required": ["accessToken", "nextRecordsUrl"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token, instance_url = await self._resolve_connection(context)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to resolve credentials: {str(e)}")

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        next_records_url = parameters.get("nextRecordsUrl")
        if not next_records_url or (next_records_url := next_records_url.strip()) == "":
            return ToolResult(
                success=False,
                output="",
                error="Next Records URL is required. This should be the nextRecordsUrl value from a previous query response.",
            )

        next_url = next_records_url if next_records_url.startswith("/") else f"/{next_records_url}"
        url = f"{instance_url}{next_url}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")