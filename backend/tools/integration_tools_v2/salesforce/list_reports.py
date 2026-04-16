from typing import Any, Dict, Tuple
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceListReportsTool(BaseTool):
    name = "salesforce_list_reports"
    description = "Get a list of reports accessible by the current user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce OAuth access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_credentials(self, context: dict | None) -> Tuple[str, str]:
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
        if not instance_url:
            raise ValueError("Salesforce instance URL not configured.")
        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folderName": {
                    "type": "string",
                    "description": "Filter reports by folder name (case-insensitive partial match)",
                },
                "searchTerm": {
                    "type": "string",
                    "description": "Search term to filter reports by name or description",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token, instance_url = await self._resolve_credentials(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{instance_url}/services/data/v59.0/analytics/reports"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    reports = data or []
                    folder_name = parameters.get("folderName")
                    if folder_name:
                        folder_lower = folder_name.lower()
                        reports = [
                            r
                            for r in reports
                            if folder_lower in (r.get("folderName") or "").lower()
                        ]
                    search_term = parameters.get("searchTerm")
                    if search_term:
                        search_lower = search_term.lower()
                        reports = [
                            r
                            for r in reports
                            if (
                                search_lower in (r.get("name") or "").lower()
                                or search_lower in (r.get("description") or "").lower()
                            )
                        ]
                    processed = {
                        "reports": reports,
                        "totalReturned": len(reports),
                        "success": True,
                    }
                    return ToolResult(
                        success=True, output=response.text, data=processed
                    )
                else:
                    return ToolResult(
                        success=False, output="", error=response.text
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")