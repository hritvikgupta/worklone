from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseCreateMultipleTool(BaseTool):
    name = "microsoft_dataverse_create_multiple"
    description = "Create multiple records of the same table type in a single request. Each record in the Targets array must include an @odata.type annotation. Recommended batch size: 100-1000 records for standard tables."
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
                    "description": "Entity set name (plural table name, e.g., accounts, contacts)",
                },
                "entityLogicalName": {
                    "type": "string",
                    "description": "Table logical name for @odata.type annotation (e.g., account, contact). Used to set Microsoft.Dynamics.CRM.{entityLogicalName} on each record.",
                },
                "records": {
                    "type": "object",
                    "description": "Array of record objects to create. Each record should contain column logical names as keys. The @odata.type annotation is added automatically.",
                },
            },
            "required": ["environmentUrl", "entitySetName", "entityLogicalName", "records"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        environment_url = parameters["environmentUrl"]
        entity_set_name = parameters["entitySetName"]
        entity_logical_name = parameters["entityLogicalName"]
        records = parameters["records"]
        
        if isinstance(records, str):
            try:
                records = json.loads(records)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for records array")
        
        if not isinstance(records, list):
            return ToolResult(success=False, output="", error="Records must be an array of objects")
        
        base_url = environment_url.rstrip("/")
        url = f"{base_url}/api/data/v9.2/{entity_set_name}/Microsoft.Dynamics.CRM.CreateMultiple"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
        }
        
        targets = [
            {**record, "@odata.type": f"Microsoft.Dynamics.CRM.{entity_logical_name}"}
            for record in records
        ]
        body = {"Targets": targets}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201]:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    error_msg = (
                        error_data.get("error", {}).get("message")
                        or f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response.json()
                ids = data.get("Ids", [])
                structured = {
                    "ids": [str(id_) for id_ in ids],
                    "count": len(ids),
                    "success": True,
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(structured),
                    data=structured,
                )
                    
        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request failed: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")