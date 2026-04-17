from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseFetchXmlQueryTool(BaseTool):
    name = "microsoft_dataverse_fetchxml_query"
    description = "Execute a FetchXML query against a Microsoft Dataverse table. FetchXML supports aggregation, grouping, linked-entity joins, and complex filtering beyond OData capabilities."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DATAVERSE_ACCESS_TOKEN",
                description="OAuth access token for Microsoft Dataverse API",
                env_var="DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("DATAVERSE_ACCESS_TOKEN",),
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
                "fetchXml": {
                    "type": "string",
                    "description": "FetchXML query string. Must include <fetch> root element and <entity> child element matching the table logical name.",
                },
            },
            "required": ["environmentUrl", "entitySetName", "fetchXml"],
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
            "Prefer": 'odata.include-annotations="*"',
        }
        
        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        fetch_xml = parameters["fetchXml"]
        encoded_fetch_xml = urllib.parse.quote(fetch_xml)
        url = f"{environment_url}/api/data/v9.2/{entity_set_name}?fetchXml={encoded_fetch_xml}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", f"Dataverse API error: {response.status_code} {response.reason_phrase}")
                    except Exception:
                        error_message = response.text or f"Dataverse API error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_message)
                
                data = response.json()
                records = data.get("value", [])
                fetch_xml_paging_cookie = data.get("@Microsoft.Dynamics.CRM.fetchxmlpagingcookie")
                more_records = data.get("@Microsoft.Dynamics.CRM.morerecords", False)
                
                transformed = {
                    "records": records,
                    "count": len(records),
                    "fetchXmlPagingCookie": fetch_xml_paging_cookie,
                    "moreRecords": more_records,
                    "success": True,
                }
                
                return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")