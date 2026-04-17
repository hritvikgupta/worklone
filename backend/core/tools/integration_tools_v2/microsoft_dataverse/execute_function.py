from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseExecuteFunctionTool(BaseTool):
    name = "Execute Microsoft Dataverse Function"
    description = "Execute a bound or unbound Dataverse function. Functions are read-only operations (e.g., RetrievePrincipalAccess, RetrieveTotalRecordCount, InitializeFrom). For bound functions, provide the entity set name and record ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                description="OAuth access token for Microsoft Dataverse API",
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
                "functionName": {
                    "type": "string",
                    "description": "Function name (e.g., RetrievePrincipalAccess, RetrieveTotalRecordCount). Do not include the Microsoft.Dynamics.CRM. namespace prefix for unbound functions.",
                },
                "entitySetName": {
                    "type": "string",
                    "description": "Entity set name for bound functions (e.g., systemusers). Leave empty for unbound functions.",
                },
                "recordId": {
                    "type": "string",
                    "description": "Record GUID for bound functions. Leave empty for unbound functions.",
                },
                "parameters": {
                    "type": "string",
                    "description": 'Function parameters as a comma-separated list of name=value pairs for the URL (e.g., "LocalizedStandardName=\'Pacific Standard Time\',LocaleId=1033"). Use @p1,@p2 aliases for complex values.',
                },
            },
            "required": ["environmentUrl", "functionName"],
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
        
        environment_url = parameters["environmentUrl"]
        function_name = parameters["functionName"]
        entity_set_name = parameters.get("entitySetName", "")
        record_id = parameters.get("recordId", "")
        func_parameters = parameters.get("parameters", "")
        
        base_url = environment_url.rstrip("/")
        param_str = f"({func_parameters})" if func_parameters else "()"
        
        if entity_set_name:
            bound_part = entity_set_name
            if record_id:
                bound_part += f"({record_id})"
            url = f"{base_url}/api/data/v9.2/{bound_part}/Microsoft.Dynamics.CRM.{function_name}{param_str}"
        else:
            url = f"{base_url}/api/data/v9.2/{function_name}{param_str}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_msg = f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        error_obj = error_data.get("error", {})
                        if error_obj.get("message"):
                            error_msg = error_obj["message"]
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")