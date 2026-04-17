from typing import Any, Dict
import httpx
import base64
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetTasksTool(BaseTool):
    name = "salesforce_get_tasks"
    description = "Get task(s) from Salesforce"
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
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "Salesforce Task ID (18-character string starting with 00T) to get a single task",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results to return (default: 100)",
                },
                "fields": {
                    "type": "string",
                    "description": "Comma-separated list of field API names to return",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Field and direction for sorting (e.g., ActivityDate DESC)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = connection.instance_url

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        task_id = parameters.get("taskId")
        default_fields = "Id,Subject,Status,Priority,ActivityDate,WhoId,WhatId,OwnerId"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        if task_id:
            fields = parameters.get("fields", default_fields)
            url = f"{instance_url}/services/data/v59.0/sobjects/Task/{task_id}?fields={fields}"
        else:
            limit = int(parameters.get("limit", 100))
            fields = parameters.get("fields", default_fields)
            order_by = parameters.get("orderBy", "ActivityDate DESC")
            query = f"SELECT {fields} FROM Task ORDER BY {order_by} LIMIT {limit}"
            url = f"{instance_url}/services/data/v59.0/query?q={urllib.parse.quote(query)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")