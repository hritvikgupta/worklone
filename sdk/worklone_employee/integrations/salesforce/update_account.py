from typing import Any, Dict, Optional
import httpx
import base64
import json
import re
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceUpdateAccountTool(BaseTool):
    name = "salesforce_update_account"
    description = "Update an existing account in Salesforce CRM"
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

    def _extract_instance_url_from_id_token(self, id_token: str) -> Optional[str]:
        try:
            base64_url = id_token.split(".")[1]
            base64_url += "=" * ((4 - len(base64_url) % 4) % 4)
            decoded_bytes = base64.urlsafe_b64decode(base64_url)
            decoded = json.loads(decoded_bytes.decode("utf-8"))
            if "profile" in decoded:
                match = re.match(r"^https://[^/]+", decoded["profile"])
                if match:
                    return match.group(0)
            elif "sub" in decoded:
                match = re.match(r"^https://[^/]+", decoded["sub"])
                if match and match.group(0) != "https://login.salesforce.com":
                    return match.group(0)
        except Exception:
            pass
        return None

    async def _resolve_credentials(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token
        instance_url: Optional[str] = None
        if hasattr(connection, "instance_url"):
            instance_url = connection.instance_url
        elif isinstance(connection, dict) and "instance_url" in connection:
            instance_url = connection["instance_url"]
        if not instance_url and context:
            instance_url = context.get("instanceUrl")
        if not instance_url and context and "idToken" in context:
            instance_url = self._extract_instance_url_from_id_token(context["idToken"])
        if not instance_url:
            raise ValueError("Salesforce instance URL is required but not provided")
        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accountId": {
                    "type": "string",
                    "description": "Salesforce Account ID to update (18-character string starting with 001)",
                },
                "name": {
                    "type": "string",
                    "description": "Account name",
                },
                "type": {
                    "type": "string",
                    "description": "Account type (e.g., Customer, Partner, Prospect)",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry (e.g., Technology, Healthcare, Finance)",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
                "website": {
                    "type": "string",
                    "description": "Website URL",
                },
                "billingStreet": {
                    "type": "string",
                    "description": "Billing street address",
                },
                "billingCity": {
                    "type": "string",
                    "description": "Billing city",
                },
                "billingState": {
                    "type": "string",
                    "description": "Billing state/province",
                },
                "billingPostalCode": {
                    "type": "string",
                    "description": "Billing postal code",
                },
                "billingCountry": {
                    "type": "string",
                    "description": "Billing country",
                },
                "description": {
                    "type": "string",
                    "description": "Account description",
                },
                "annualRevenue": {
                    "type": "string",
                    "description": "Annual revenue as a number",
                },
                "numberOfEmployees": {
                    "type": "string",
                    "description": "Number of employees as an integer",
                },
            },
            "required": ["accountId"],
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

        account_id = parameters["accountId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Account/{account_id}"

        body: Dict[str, Any] = {}
        field_mapping = {
            "name": "Name",
            "type": "Type",
            "industry": "Industry",
            "phone": "Phone",
            "website": "Website",
            "billingStreet": "BillingStreet",
            "billingCity": "BillingCity",
            "billingState": "BillingState",
            "billingPostalCode": "BillingPostalCode",
            "billingCountry": "BillingCountry",
            "description": "Description",
        }
        for param_key, sf_key in field_mapping.items():
            if param_key in parameters and parameters[param_key]:
                body[sf_key] = parameters[param_key]

        if "annualRevenue" in parameters and parameters["annualRevenue"]:
            try:
                body["AnnualRevenue"] = float(parameters["annualRevenue"])
            except (ValueError, TypeError):
                pass
        if "numberOfEmployees" in parameters and parameters["numberOfEmployees"]:
            try:
                body["NumberOfEmployees"] = int(parameters["numberOfEmployees"])
            except (ValueError, TypeError):
                pass

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"id": account_id, "updated": True},
                    )
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data:
                            error_msg = error_data[0].get("message", str(error_data[0]))
                        elif isinstance(error_data, dict):
                            error_msg = error_data.get("message", error_msg)
                    except json.JSONDecodeError:
                        pass
                    return ToolResult(
                        success=False, output="", error=error_msg or "Failed to update account in Salesforce"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")