from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class SalesforceGetCasesTool(BaseTool):
    name = "Get Cases from Salesforce"
    description = "Get case(s) from Salesforce"
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

    async def _resolve_connection(self, context: dict | None) -> Any:
        return await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "caseId": {
                    "type": "string",
                    "description": "Salesforce Case ID (18-character string starting with 500) to get a single case",
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
                    "description": "Field and direction for sorting (e.g., CreatedDate DESC)",
                },
            },
            "required": [],
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

        case_id = parameters.get("caseId")
        fields_default = "Id,CaseNumber,Subject,Status,Priority,Origin,ContactId,AccountId"

        if case_id:
            fields = parameters.get("fields", fields_default)
            fields_param = quote(fields)
            url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Case/{case_id}?fields={fields_param}"
        else:
            limit_num = int(parameters.get("limit", 100))
            fields = parameters.get("fields", fields_default)
            order_by = parameters.get("orderBy", "CreatedDate DESC")
            query = f"SELECT {fields} FROM Case ORDER BY {order_by} LIMIT {limit_num}"
            q_encoded = quote(query)
            url = f"{instance_url.rstrip('/')}/services/data/v59.0/query?q={q_encoded}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if case_id:
                        output = {
                            "case": data,
                            "success": True,
                        }
                    else:
                        cases = data.get("records", [])
                        output = {
                            "cases": cases,
                            "paging": {
                                "nextRecordsUrl": data.get("nextRecordsUrl"),
                                "totalSize": data.get("totalSize", len(cases)),
                                "done": data.get("done") != False,
                            },
                            "metadata": {
                                "totalReturned": len(cases),
                                "hasMore": data.get("done") == False,
                            },
                            "success": True,
                        }
                    return ToolResult(success=True, output=output, data=data)
                else:
                    try:
                        err_data = response.json()
                        if isinstance(err_data, list) and err_data:
                            error_msg = err_data[0].get("message", response.text)
                        else:
                            error_msg = err_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")