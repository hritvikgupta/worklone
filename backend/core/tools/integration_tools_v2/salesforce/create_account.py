from typing import Any, Dict, Tuple
import httpx
import base64
import json
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceCreateAccountTool(BaseTool):
    name = "salesforce_create_account"
    description = "Create a new account in Salesforce CRM"
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

    async def _resolve_auth(self, context: dict | None) -> Tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token

        id_token = context.get("idToken") if context else None
        instance_url = context.get("instanceUrl") if context else None

        if not instance_url and id_token:
            try:
                parts = id_token.split(".")
                if len(parts) >= 2:
                    base64_url = parts[1]
                    missing_padding = len(base64_url) % 4
                    if missing_padding:
                        base64_url += "=" * (4 - missing_padding)
                    base64_encoded = base64_url.replace("-", "+").replace("_", "/")
                    json_payload = base64.b64decode(base64_encoded)
                    decoded_str = json_payload.decode("utf-8")
                    decoded = json.loads(decoded_str)
                    if "profile" in decoded:
                        match = re.match(r"^(https://[^/]+)", decoded["profile"])
                        if match:
                            instance_url = match.group(1)
                    elif "sub" in decoded:
                        match = re.match(r"^(https://[^/]+)", decoded["sub"])
                        if match and match.group(1) != "https://login.salesforce.com":
                            instance_url = match.group(1)
            except Exception:
                pass

        if not instance_url:
            raise ValueError("Salesforce instance URL is required but not provided")

        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Account name (required)",
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
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token, instance_url = await self._resolve_auth(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url}/services/data/v59.0/sobjects/Account"

        body: Dict[str, Any] = {
            "Name": parameters["name"],
        }
        if ptype := parameters.get("type"):
            body["Type"] = ptype
        if pindustry := parameters.get("industry"):
            body["Industry"] = pindustry
        if pphone := parameters.get("phone"):
            body["Phone"] = pphone
        if pwebsite := parameters.get("website"):
            body["Website"] = pwebsite
        if pbilling_street := parameters.get("billingStreet"):
            body["BillingStreet"] = pbilling_street
        if pbilling_city := parameters.get("billingCity"):
            body["BillingCity"] = pbilling_city
        if pbilling_state := parameters.get("billingState"):
            body["BillingState"] = pbilling_state
        if pbilling_postal_code := parameters.get("billingPostalCode"):
            body["BillingPostalCode"] = pbilling_postal_code
        if pbilling_country := parameters.get("billingCountry"):
            body["BillingCountry"] = pbilling_country
        if pdescription := parameters.get("description"):
            body["Description"] = pdescription
        if annual_revenue := parameters.get("annualRevenue"):
            body["AnnualRevenue"] = float(annual_revenue)
        if num_employees := parameters.get("numberOfEmployees"):
            body["NumberOfEmployees"] = int(num_employees)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if 200 <= response.status_code < 300:
                    return ToolResult(success=True, output=response.text, data=response.json())
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