from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseAssociateTool(BaseTool):
    name = "microsoft_dataverse_associate"
    description = "Associate two records in Microsoft Dataverse via a navigation property. Creates a relationship between a source record and a target record. Supports both collection-valued (POST) and single-valued (PUT) navigation properties."
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
            context_token_keys=("accessToken",),
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
                "targetEntitySetName": {
                    "type": "string",
                    "description": "Target entity set name (e.g., contacts)",
                },
                "targetRecordId": {
                    "type": "string",
                    "description": "Target record GUID to associate",
                },
                "navigationType": {
                    "type": "string",
                    "description": "Type of navigation property: \"collection\" (default, uses POST) or \"single\" (uses PUT for lookup fields)",
                },
            },
            "required": [
                "environmentUrl",
                "entitySetName",
                "recordId",
                "navigationProperty",
                "targetEntitySetName",
                "targetRecordId",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
        }

        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        navigation_property = parameters["navigationProperty"]
        target_entity_set_name = parameters["targetEntitySetName"]
        target_record_id = parameters["targetRecordId"]
        navigation_type = parameters.get("navigationType", "collection")

        url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id})/{navigation_property}/$ref"

        body = {
            "@odata.id": f"{environment_url}/api/data/v9.2/{target_entity_set_name}({target_record_id})",
        }

        http_method = "PUT" if navigation_type == "single" else "POST"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(http_method, url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    params_echo = {
                        "entitySetName": entity_set_name,
                        "recordId": record_id,
                        "navigationProperty": navigation_property,
                        "targetEntitySetName": target_entity_set_name,
                        "targetRecordId": target_record_id,
                    }
                    data = {"success": True, **params_echo}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and "error" in error_data:
                            error_msg = error_data["error"].get("message", error_msg)
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")