from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseDisassociateTool(BaseTool):
    name = "microsoft_dataverse_disassociate"
    description = "Remove an association between two records in Microsoft Dataverse. For collection-valued navigation properties, provide the target record ID. For single-valued navigation properties, only the navigation property name is needed."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                description="Access token for Microsoft Dataverse API",
                env_var="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("MICROSOFT_DATAVERSE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "environmentUrl": {
                    "type": "string",
                    "description": "Dataverse environment URL (e.g., https://myorg.crm.dynamics.com)",
                },
                "entitySetName": {
                    "type": "string",
                    "description": "Source entity set name (e.g., accounts)",
                },
                "recordId": {
                    "type": "string",
                    "description": "Source record GUID",
                },
                "navigationProperty": {
                    "type": "string",
                    "description": "Navigation property name (e.g., contact_customer_accounts for collection-valued, or parentcustomerid_account for single-valued)",
                },
                "targetRecordId": {
                    "type": "string",
                    "description": "Target record GUID (required for collection-valued navigation properties, omit for single-valued)",
                },
            },
            "required": ["environmentUrl", "entitySetName", "recordId", "navigationProperty"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
        }
        
        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        navigation_property = parameters["navigationProperty"]
        target_record_id = parameters.get("targetRecordId")
        
        if target_record_id:
            url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id})/{navigation_property}({target_record_id})/$ref"
        else:
            url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id})/{navigation_property}/$ref"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = {
                        "success": True,
                        "entitySetName": entity_set_name,
                        "recordId": record_id,
                        "navigationProperty": navigation_property,
                    }
                    if target_record_id:
                        data["targetRecordId"] = target_record_id
                    return ToolResult(success=True, output="", data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text or f"Dataverse API error: {response.status_code} {response.reason_phrase}")
                    except Exception:
                        error_msg = response.text or f"Dataverse API error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")