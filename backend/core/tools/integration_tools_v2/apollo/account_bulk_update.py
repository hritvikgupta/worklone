from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ApolloAccountBulkUpdateTool(BaseTool):
    name = "apollo_account_bulk_update"
    description = "Update up to 1000 existing accounts at once in your Apollo database (higher limit than contacts!). Each account must include an id field. Master key required."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key (master key required)",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "apollo",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("APOLLO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accounts": {
                    "type": "array",
                    "description": "Array of accounts to update (max 1000). Each account must include id field, and optionally name, website_url, phone, owner_id",
                },
            },
            "required": ["accounts"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": access_token,
        }
        
        url = "https://api.apollo.io/api/v1/accounts/bulk_update"
        accounts = parameters.get("accounts", [])[:1000]
        body = {"accounts": accounts}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Apollo API error: {response.status_code} - {error_text}"
                    )
                
                data = response.json()
                updated_accounts_list = data.get("accounts") or data.get("updated_accounts") or []
                failed_accounts_list = data.get("failed_accounts") or []
                total_submitted = len(data.get("accounts", []))
                updated_count = len(data.get("updated_accounts", [])) or len(data.get("accounts", []))
                failed_count = len(data.get("failed_accounts", []))
                
                output_data = {
                    "updated_accounts": updated_accounts_list,
                    "failed_accounts": failed_accounts_list,
                    "total_submitted": total_submitted,
                    "updated": updated_count,
                    "failed": failed_count,
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")