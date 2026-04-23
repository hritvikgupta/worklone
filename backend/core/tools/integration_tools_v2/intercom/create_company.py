from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomCreateCompanyTool(BaseTool):
    name = "intercom_create_company"
    description = "Create or update a company in Intercom"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_body(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "company_id": parameters["company_id"],
        }
        str_fields = ["name", "website", "plan", "industry"]
        for f in str_fields:
            val = parameters.get(f)
            if val:
                body[f] = val
        num_fields = ["size", "monthly_spend", "remote_created_at"]
        for f in num_fields:
            val = parameters.get(f)
            if val is not None:
                body[f] = val
        custom_attr = parameters.get("custom_attributes")
        if custom_attr:
            try:
                body["custom_attributes"] = json.loads(custom_attr)
            except json.JSONDecodeError:
                pass
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "company_id": {
                    "type": "string",
                    "description": "Your unique identifier for the company",
                },
                "name": {
                    "type": "string",
                    "description": "The name of the company",
                },
                "website": {
                    "type": "string",
                    "description": "The company website",
                },
                "plan": {
                    "type": "string",
                    "description": "The company plan name",
                },
                "size": {
                    "type": "number",
                    "description": "The number of employees in the company",
                },
                "industry": {
                    "type": "string",
                    "description": "The industry the company operates in",
                },
                "monthly_spend": {
                    "type": "number",
                    "description": "How much revenue the company generates for your business. Note: This field truncates floats to whole integers (e.g., 155.98 becomes 155)",
                },
                "custom_attributes": {
                    "type": "string",
                    "description": "Custom attributes as JSON object",
                },
                "remote_created_at": {
                    "type": "number",
                    "description": "The time the company was created by you as a Unix timestamp",
                },
            },
            "required": ["company_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        url = "https://api.intercom.io/companies"
        body = self._build_body(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")