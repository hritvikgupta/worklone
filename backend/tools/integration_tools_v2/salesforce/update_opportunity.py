from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceUpdateOpportunityTool(BaseTool):
    name = "salesforce_update_opportunity"
    description = "Update an existing opportunity"
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

    async def _resolve_connection(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken", "idToken", "instanceUrl"),
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
                "opportunityId": {
                    "type": "string",
                    "description": "Salesforce Opportunity ID to update (18-character string starting with 006)",
                },
                "name": {
                    "type": "string",
                    "description": "Opportunity name",
                },
                "stageName": {
                    "type": "string",
                    "description": "Stage name (e.g., Prospecting, Qualification, Closed Won)",
                },
                "closeDate": {
                    "type": "string",
                    "description": "Close date in YYYY-MM-DD format",
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
            "required": ["opportunityId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token, instance_url = await self._resolve_connection(context)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to resolve credentials: {str(e)}")

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Access token or instance URL not configured.")

        opportunity_id = parameters["opportunityId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Opportunity/{opportunity_id}"

        body: Dict[str, Any] = {}
        name = parameters.get("name")
        if name:
            body["Name"] = name
        stage_name = parameters.get("stageName")
        if stage_name:
            body["StageName"] = stage_name
        close_date = parameters.get("closeDate")
        if close_date:
            body["CloseDate"] = close_date
        account_id = parameters.get("accountId")
        if account_id:
            body["AccountId"] = account_id
        amount = parameters.get("amount")
        if amount:
            body["Amount"] = float(amount)
        probability = parameters.get("probability")
        if probability:
            body["Probability"] = int(probability)
        desc = parameters.get("description")
        if desc:
            body["Description"] = desc

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    result_data = {
                        "id": opportunity_id,
                        "updated": True,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(result_data),
                        data=result_data,
                    )
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data:
                            error_msg = error_data[0].get("message", str(error_data[0]))
                        else:
                            error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")