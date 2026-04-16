from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseSearchTool(BaseTool):
    name = "microsoft_dataverse_search"
    description = "Perform a full-text relevance search across Microsoft Dataverse tables. Requires Dataverse Search to be enabled on the environment. Supports simple and Lucene query syntax."
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
            context_token_keys=("access_token",),
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
                "searchTerm": {
                    "type": "string",
                    "description": "Search text (1-100 chars). Supports simple syntax: + (AND), | (OR), - (NOT), * (wildcard), \"exact phrase\"",
                },
                "entities": {
                    "type": "string",
                    "description": "JSON array of search entity configs. Each object: {\"Name\":\"account\",\"SelectColumns\":[\"name\"],\"SearchColumns\":[\"name\"],\"Filter\":\"statecode eq 0\"}",
                },
                "filter": {
                    "type": "string",
                    "description": "Global OData filter applied across all entities (e.g., \"createdon gt 2024-01-01\")",
                },
                "facets": {
                    "type": "string",
                    "description": "JSON array of facet specifications (e.g., [\"entityname,count:100\",\"ownerid,count:100\"])",
                },
                "top": {
                    "type": "number",
                    "description": "Maximum number of results (default: 50, max: 100)",
                },
                "skip": {
                    "type": "number",
                    "description": "Number of results to skip for pagination",
                },
                "orderBy": {
                    "type": "string",
                    "description": "JSON array of sort expressions (e.g., [\"createdon desc\"])",
                },
                "searchMode": {
                    "type": "string",
                    "description": 'Search mode: "any" (default, match any term) or "all" (match all terms)',
                },
                "searchType": {
                    "type": "string",
                    "description": 'Query type: "simple" (default) or "lucene" (enables regex, fuzzy, proximity, boosting)',
                },
            },
            "required": ["environmentUrl", "searchTerm"],
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
        url = f"{environment_url}/api/data/v9.2/searchquery"
        
        body = {
            "search": parameters["searchTerm"],
            "count": True,
        }
        if "entities" in parameters:
            body["entities"] = parameters["entities"]
        if "filter" in parameters:
            body["filter"] = parameters["filter"]
        if "facets" in parameters:
            body["facets"] = parameters["facets"]
        if "top" in parameters:
            body["top"] = parameters["top"]
        if "skip" in parameters:
            body["skip"] = parameters["skip"]
        if "orderBy" in parameters:
            body["orderby"] = parameters["orderBy"]
        
        options = {}
        if "searchMode" in parameters:
            options["searchmode"] = parameters["searchMode"]
        if "searchType" in parameters:
            options["querytype"] = parameters["searchType"]
        if options:
            body["options"] = json.dumps(options).replace('"', "'")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                    
                    parsed_response = data.get("response")
                    if isinstance(parsed_response, str):
                        try:
                            parsed_response = json.loads(parsed_response)
                        except json.JSONDecodeError:
                            parsed_response = {}
                    else:
                        parsed_response = parsed_response or {}
                    
                    results = parsed_response.get("Value", [])
                    total_count = parsed_response.get("Count", 0)
                    facets = parsed_response.get("Facets")
                    
                    output_data = {
                        "results": results,
                        "totalCount": total_count,
                        "count": len(results),
                        "facets": facets,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message") or f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    except json.JSONDecodeError:
                        error_message = response.text or f"HTTP {response.status_code}"
                    return ToolResult(success=False, output="", error=error_message)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")