from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetLeadsTool(BaseTool):
    name = "salesforce_get_leads"
    description = "Get lead(s) from Salesforce"
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

    async def _resolve_credentials(self, context: dict | None) -> Dict[str, str]:
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
        return {"access_token": access_token, "instance_url": instance_url}

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "leadId": {
                    "type": "string",
                    "description": "Salesforce Lead ID (18-character string starting with 00Q) to get a single lead",
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
                    "description": "Field and direction for sorting (e.g., LastName ASC)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        creds = await self._resolve_credentials(context)
        access_token = creds.get("access_token")
        instance_url = creds.get("instance_url")
        
        if self._is_placeholder_token(access_token or "") or self._is_placeholder_token(str(instance_url or "")):
            return ToolResult(success=False, output="", error="Access token or instance URL not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        lead_id = parameters.get("leadId")
        fields = parameters.get("fields")
        limit_str = parameters.get("limit")
        order_by = parameters.get("orderBy")
        
        if lead_id:
            fields_str = fields or "Id,FirstName,LastName,Company,Email,Phone,Status,LeadSource"
            url = f"{instance_url}/services/data/v59.0/sobjects/Lead/{lead_id}?fields={fields_str}"
        else:
            limit_num = int(limit_str) if limit_str else 100
            fields_str = fields or "Id,FirstName,LastName,Company,Email,Phone,Status,LeadSource"
            order_by_str = order_by or "LastName ASC"
            query = f"SELECT {fields_str} FROM Lead ORDER BY {order_by_str} LIMIT {limit_num}"
            encoded_query = urllib.parse.quote(query)
            url = f"{instance_url}/services/data/v59.0/query?q={encoded_query}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
            if response.status_code in [200, 201, 204]:
                data = response.json()
                if lead_id:
                    output = {
                        "lead": data,
                        "singleLead": True,
                        "success": True,
                    }
                else:
                    leads = data.get("records", [])
                    data_done = data.get("done")
                    output = {
                        "leads": leads,
                        "paging": {
                            "nextRecordsUrl": data.get("nextRecordsUrl"),
                            "totalSize": data.get("totalSize", len(leads)),
                            "done": data_done != False,
                        },
                        "metadata": {
                            "totalReturned": len(leads),
                            "hasMore": data_done == False,
                        },
                        "success": True,
                    }
                return ToolResult(success=True, output=json.dumps(output, indent=2), data=output)
            else:
                error_msg = response.text
                try:
                    err_data = response.json()
                    if isinstance(err_data, list) and err_data:
                        error_msg = err_data[0].get("message", response.text)
                    elif isinstance(err_data, dict):
                        error_msg = err_data.get("message", response.text)
                except ValueError:
                    pass
                return ToolResult(success=False, output="", error=error_msg)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")