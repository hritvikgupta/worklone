from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceUpdateLeadTool(BaseTool):
    name = "salesforce_update_lead"
    description = "Update an existing lead"
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
            context_token_keys=("accessToken", "idToken", "instanceUrl"),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "leadId": {
                    "type": "string",
                    "description": "Salesforce Lead ID to update (18-character string starting with 00Q)",
                },
                "lastName": {
                    "type": "string",
                    "description": "Last name",
                },
                "company": {
                    "type": "string",
                    "description": "Company name",
                },
                "firstName": {
                    "type": "string",
                    "description": "First name",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
                "status": {
                    "type": "string",
                    "description": "Lead status (e.g., Open, Working, Closed)",
                },
                "leadSource": {
                    "type": "string",
                    "description": "Lead source (e.g., Web, Referral, Campaign)",
                },
                "title": {
                    "type": "string",
                    "description": "Job title",
                },
                "description": {
                    "type": "string",
                    "description": "Lead description",
                },
            },
            "required": ["leadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = connection.instance_url

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        lead_id = parameters["leadId"]
        url = f"{instance_url}/services/data/v59.0/sobjects/Lead/{lead_id}"

        body: Dict[str, Any] = {}
        fields_map = {
            "lastName": "LastName",
            "company": "Company",
            "firstName": "FirstName",
            "email": "Email",
            "phone": "Phone",
            "status": "Status",
            "leadSource": "LeadSource",
            "title": "Title",
            "description": "Description",
        }
        for py_key, sf_key in fields_map.items():
            if py_key in parameters and parameters[py_key]:
                body[sf_key] = parameters[py_key]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = {
                        "id": lead_id,
                        "updated": True,
                    }
                    return ToolResult(success=True, output=str(data), data=data)
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data:
                            error_msg = error_data[0].get("message", "Failed to update lead")
                        elif isinstance(error_data, dict):
                            error_msg = error_data.get("message", "Failed to update lead")
                        else:
                            error_msg = "Failed to update lead"
                    except Exception:
                        error_msg = response.text or "Failed to update lead"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")