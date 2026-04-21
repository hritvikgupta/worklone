from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceCreateTaskTool(BaseTool):
    name = "salesforce_create_task"
    description = "Create a new task"
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

    async def _resolve_connection(self, context: dict | None) -> Dict[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return {
            "access_token": connection.access_token,
            "instance_url": connection.instance_url,
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Task subject (required)",
                },
                "status": {
                    "type": "string",
                    "description": "Status (e.g., Not Started, In Progress, Completed)",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (e.g., Low, Normal, High)",
                },
                "activityDate": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
                "whoId": {
                    "type": "string",
                    "description": "Related Contact ID (003...) or Lead ID (00Q...)",
                },
                "whatId": {
                    "type": "string",
                    "description": "Related Account ID (001...) or Opportunity ID (006...)",
                },
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
            },
            "required": ["subject"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection["access_token"]
        instance_url = connection["instance_url"]

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Task"

        body = {"Subject": parameters["subject"]}
        field_mappings = {
            "Status": "status",
            "Priority": "priority",
            "ActivityDate": "activityDate",
            "WhoId": "whoId",
            "WhatId": "whatId",
            "Description": "description",
        }
        for api_field, param_field in field_mappings.items():
            param_value = parameters.get(param_field)
            if param_value:
                body[api_field] = param_value

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")