from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOrganizationBulkEnrichTool(BaseTool):
    name = "apollo_organization_bulk_enrich"
    description = "Enrich data for up to 10 organizations at once using Apollo"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str | None:
        if context is None:
            return None
        api_key = context.get("apiKey")
        if self._is_placeholder_token(api_key or ""):
            return None
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "organizations": {
                    "type": "array",
                    "description": "Array of organizations to enrich (max 10)",
                },
            },
            "required": ["organizations"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if not api_key:
            return ToolResult(success=False, output="", error="Apollo API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        url = "https://api.apollo.io/api/v1/organizations/bulk_enrich"

        json_body = {
            "details": parameters.get("organizations", [])[:10],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")