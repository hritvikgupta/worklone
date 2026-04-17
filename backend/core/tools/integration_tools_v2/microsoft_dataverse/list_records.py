from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseListRecordsTool(BaseTool):
    name = "microsoft_dataverse_list_records"
    description = "Query and list records from a Microsoft Dataverse table. Supports OData query options for filtering, selecting columns, ordering, and pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PROVIDER_ACCESS_TOKEN",
                description="Access token",
                env_var="PROVIDER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PROVIDER_ACCESS_TOKEN",),
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
                "select": {
                    "type": "string",
                    "description": "Comma-separated list of columns to return (OData $select)",
                },
                "filter": {
                    "type": "string",
                    "description": "OData $filter expression (e.g., statecode eq 0)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "OData $orderby expression (e.g., name asc, createdon desc)",
                },
                "top": {
                    "type": "number",
                    "description": "Maximum number of records to return (OData $top)",
                },
                "expand": {
                    "type": "string",
                    "description": "Navigation properties to expand (OData $expand)",
                },
                "count": {
                    "type": "string",
                    "description": 'Set to "true" to include total record count in response (OData $count)',
                },
            },
            "required": ["environmentUrl", "entitySetName"],
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
            "Prefer": 'odata.include-annotations="*",odata.maxpagesize=100',
        }
        
        env_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        url = f"{env_url}/api/data/v9.2/{entity_set_name}"
        
        query_params: Dict[str, str] = {}
        select = parameters.get("select")
        if select:
            query_params["$select"] = select
        filter_ = parameters.get("filter")
        if filter_:
            query_params["$filter"] = filter_
        order_by = parameters.get("orderBy")
        if order_by:
            query_params["$orderby"] = order_by
        top = parameters.get("top")
        if top is not None:
            query_params["$top"] = str(top)
        expand = parameters.get("expand")
        if expand:
            query_params["$expand"] = expand
        count = parameters.get("count")
        if count:
            query_params["$count"] = count
        
        if query_params:
            query_string = urllib.parse.urlencode(query_params)
            url += f"?{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")