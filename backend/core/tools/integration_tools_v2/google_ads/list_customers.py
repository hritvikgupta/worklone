from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleAdsListCustomersTool(BaseTool):
    name = "google_ads_list_customers"
    description = "List all Google Ads customer accounts accessible by the authenticated user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_ADS_ACCESS_TOKEN",
                description="Access token for the Google Ads API",
                env_var="GOOGLE_ADS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="GOOGLE_ADS_DEVELOPER_TOKEN",
                description="Google Ads API developer token",
                env_var="GOOGLE_ADS_DEVELOPER_TOKEN",
                required=True,
                auth_type="api_key",
            ),
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-ads",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_ADS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        developer_token = (context or {}).get("developerToken", "")
        if self._is_placeholder_token(developer_token):
            return ToolResult(success=False, output="", error="Developer token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
        }
        
        url = "https://googleads.googleapis.com/v19/customers:listAccessibleCustomers"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
            
            data: dict[str, Any] = {}
            try:
                data = response.json()
            except:
                pass
            
            if response.status_code == 200:
                resource_names: list[str] = data.get("resourceNames", [])
                customer_ids = [rn.replace("customers/", "") for rn in resource_names]
                result = {
                    "customerIds": customer_ids,
                    "totalCount": len(customer_ids),
                }
                return ToolResult(success=True, output=str(result), data=result)
            else:
                error_dict = data.get("error", {})
                error_message = error_dict.get("message")
                if not error_message:
                    details = error_dict.get("details", [])
                    if details and isinstance(details, list) and len(details) > 0:
                        first_detail = details[0]
                        if isinstance(first_detail, dict):
                            errors = first_detail.get("errors", [])
                            if errors and isinstance(errors, list) and len(errors) > 0:
                                first_error = errors[0]
                                if isinstance(first_error, dict):
                                    error_message = first_error.get("message")
                if not error_message:
                    error_message = "Unknown error"
                return ToolResult(success=False, output="", error=error_message)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")