from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetOpportunitiesTool(BaseTool):
    name = "salesforce_get_opportunities"
    description = "Get opportunity(ies) from Salesforce"
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
                "opportunityId": {
                    "type": "string",
                    "description": "Salesforce Opportunity ID (18-character string starting with 006) to get a single opportunity",
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
                    "description": "Field and direction for sorting (e.g., CloseDate DESC)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        opportunity_id = parameters.get("opportunityId")
        fields_default = "Id,Name,AccountId,Amount,StageName,CloseDate,Probability"

        if opportunity_id:
            fields = parameters.get("fields", fields_default)
            url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Opportunity/{opportunity_id}?fields={fields}"
        else:
            limit_val = parameters.get("limit", "100")
            limit = int(limit_val) if limit_val else 100
            fields = parameters.get("fields", fields_default)
            order_by = parameters.get("orderBy", "CloseDate DESC")
            query = f"SELECT {fields} FROM Opportunity ORDER BY {order_by} LIMIT {limit}"
            encoded_query = urllib.parse.quote(query)
            url = f"{instance_url.rstrip('/')}/services/data/v59.0/query?q={encoded_query}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()

                    if opportunity_id:
                        output = {
                            "opportunity": data,
                            "success": True,
                        }
                    else:
                        opportunities = data.get("records", [])
                        done_val = data.get("done")
                        paging = {
                            "nextRecordsUrl": data.get("nextRecordsUrl"),
                            "totalSize": data.get("totalSize", len(opportunities)),
                            "done": done_val is not False,
                        }
                        metadata = {
                            "totalReturned": len(opportunities),
                            "hasMore": not bool(done_val),
                        }
                        output = {
                            "opportunities": opportunities,
                            "paging": paging,
                            "metadata": metadata,
                            "success": True,
                        }
                    return ToolResult(success=True, output=output, data=data)
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data:
                            error_msg = error_data[0].get("message", "") if isinstance(error_data[0], dict) else str(error_data[0])
                        elif isinstance(error_data, dict):
                            error_msg = error_data.get("message", "")
                        else:
                            error_msg = str(error_data)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")