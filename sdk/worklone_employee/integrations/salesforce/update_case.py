from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceUpdateCaseTool(BaseTool):
    name = "salesforce_update_case"
    description = "Update an existing case"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce Access Token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token, getattr(connection, "instance_url", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "caseId": {
                    "type": "string",
                    "description": "Salesforce Case ID to update (18-character string starting with 500)",
                },
                "subject": {
                    "type": "string",
                    "description": "Case subject",
                },
                "status": {
                    "type": "string",
                    "description": "Status (e.g., New, Working, Escalated, Closed)",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (e.g., Low, Medium, High)",
                },
                "description": {
                    "type": "string",
                    "description": "Case description",
                },
            },
            "required": ["caseId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token, instance_url = await self._resolve_connection(context)

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        case_id = parameters["caseId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Case/{case_id}"

        body: Dict[str, Any] = {}
        if parameters.get("subject"):
            body["Subject"] = parameters["subject"]
        if parameters.get("status"):
            body["Status"] = parameters["status"]
        if parameters.get("priority"):
            body["Priority"] = parameters["priority"]
        if parameters.get("description"):
            body["Description"] = parameters["description"]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 204]:
                    result_data = {"id": case_id, "updated": True}
                    return ToolResult(
                        success=True,
                        output=str(result_data),
                        data=result_data,
                    )
                else:
                    error_msg = response.text
                    try:
                        data = response.json()
                        if isinstance(data, list) and data:
                            error_msg = data[0].get("message", str(data[0]))
                        elif isinstance(data, dict):
                            error_msg = data.get("message", response.text)
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")