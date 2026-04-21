from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceDescribeObjectTool(BaseTool):
    name = "salesforce_describe_object"
    description = "Get metadata and field information for a Salesforce object"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "objectName": {
                    "type": "string",
                    "description": "Salesforce object API name (e.g., Account, Contact, Lead, Custom_Object__c)",
                },
            },
            "required": ["objectName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        instance_url = context.get("instanceUrl") if context else None
        if not instance_url:
            return ToolResult(success=False, output="", error="Salesforce instance URL not configured.")
        
        object_name = (parameters.get("objectName") or "").strip()
        if not object_name:
            return ToolResult(
                success=False,
                output="",
                error="Object Name is required. Please provide a valid Salesforce object API name (e.g., Account, Contact, Lead, Custom_Object__c).",
            )
        
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/{object_name}/describe"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")