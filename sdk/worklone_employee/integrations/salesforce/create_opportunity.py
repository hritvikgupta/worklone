from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceCreateOpportunityTool(BaseTool):
    name = "salesforce_create_opportunity"
    description = "Create a new opportunity"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> Any:
        return await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("salesforce_token",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Opportunity name (required)",
                },
                "stageName": {
                    "type": "string",
                    "description": "Stage name (required, e.g., Prospecting, Qualification, Closed Won)",
                },
                "closeDate": {
                    "type": "string",
                    "description": "Close date in YYYY-MM-DD format (required)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Salesforce Account ID (18-character string starting with 001)",
                },
                "amount": {
                    "type": "string",
                    "description": "Deal amount as a number",
                },
                "probability": {
                    "type": "string",
                    "description": "Win probability as integer (0-100)",
                },
                "description": {
                    "type": "string",
                    "description": "Opportunity description",
                },
            },
            "required": ["name", "stageName", "closeDate"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Access token or instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Opportunity"

        body = {
            "Name": parameters["name"],
            "StageName": parameters["stageName"],
            "CloseDate": parameters["closeDate"],
        }

        account_id = parameters.get("accountId")
        if account_id:
            body["AccountId"] = account_id

        amount_str = parameters.get("amount")
        if amount_str:
            body["Amount"] = float(amount_str)

        probability_str = parameters.get("probability")
        if probability_str:
            body["Probability"] = int(float(probability_str))

        description = parameters.get("description")
        if description:
            body["Description"] = description

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")