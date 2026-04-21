from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceCreateCaseTool(BaseTool):
    name = "salesforce_create_case"
    description = "Create a new case"
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
        return connection.access_token, getattr(connection, "instance_url", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Case subject (required)",
                },
                "status": {
                    "type": "string",
                    "description": "Status (e.g., New, Working, Escalated)",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (e.g., Low, Medium, High)",
                },
                "origin": {
                    "type": "string",
                    "description": "Origin (e.g., Phone, Email, Web)",
                },
                "contactId": {
                    "type": "string",
                    "description": "Salesforce Contact ID (18-character string starting with 003)",
                },
                "accountId": {
                    "type": "string",
                    "description": "Salesforce Account ID (18-character string starting with 001)",
                },
                "description": {
                    "type": "string",
                    "description": "Case description",
                },
            },
            "required": ["subject"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token, instance_url = await self._resolve_connection(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url}/services/data/v59.0/sobjects/Case"

        body: Dict[str, Any] = {"Subject": parameters["subject"]}
        status = parameters.get("status")
        if status:
            body["Status"] = status
        priority = parameters.get("priority")
        if priority:
            body["Priority"] = priority
        origin = parameters.get("origin")
        if origin:
            body["Origin"] = origin
        contact_id = parameters.get("contactId")
        if contact_id:
            body["ContactId"] = contact_id
        account_id = parameters.get("accountId")
        if account_id:
            body["AccountId"] = account_id
        description = parameters.get("description")
        if description:
            body["Description"] = description

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())

                try:
                    data = response.json()
                except Exception:
                    data = None

                error_msg = "Failed to create case"
                if data:
                    if isinstance(data, list) and data and isinstance(data[0], dict) and "message" in data[0]:
                        error_msg = data[0]["message"]
                    elif isinstance(data, dict) and "message" in data:
                        error_msg = data["message"]

                return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")