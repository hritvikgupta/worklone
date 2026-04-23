from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOpportunityUpdateTool(BaseTool):
    name = "apollo_opportunity_update"
    description = "Update an existing deal/opportunity in your Apollo database"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        return (context or {}).get("APOLLO_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "opportunity_id": {
                    "type": "string",
                    "description": "ID of the opportunity to update (e.g., \"opp_abc123\")",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the opportunity/deal (e.g., \"Enterprise License - Q1\")",
                },
                "amount": {
                    "type": "number",
                    "description": "Monetary value of the opportunity",
                },
                "stage_id": {
                    "type": "string",
                    "description": "ID of the deal stage",
                },
                "owner_id": {
                    "type": "string",
                    "description": "User ID of the opportunity owner",
                },
                "close_date": {
                    "type": "string",
                    "description": "Expected close date (ISO 8601 format)",
                },
                "description": {
                    "type": "string",
                    "description": "Description or notes about the opportunity",
                },
            },
            "required": ["opportunity_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        opportunity_id = parameters["opportunity_id"]
        url = f"https://api.apollo.io/api/v1/opportunities/{opportunity_id}"

        body: dict = {}
        if parameters.get("name"):
            body["name"] = parameters["name"]
        if parameters.get("amount") is not None:
            body["amount"] = parameters["amount"]
        if parameters.get("stage_id"):
            body["stage_id"] = parameters["stage_id"]
        if parameters.get("owner_id"):
            body["owner_id"] = parameters["owner_id"]
        if parameters.get("close_date"):
            body["close_date"] = parameters["close_date"]
        if parameters.get("description"):
            body["description"] = parameters["description"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")