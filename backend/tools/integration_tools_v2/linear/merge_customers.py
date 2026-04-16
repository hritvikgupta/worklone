from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearMergeCustomersTool(BaseTool):
    name = "linear_merge_customers"
    description = "Merge two customers in Linear by moving all data from source to target"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token for Linear",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sourceCustomerId": {
                    "type": "string",
                    "description": "Source customer ID (will be deleted after merge)",
                },
                "targetCustomerId": {
                    "type": "string",
                    "description": "Target customer ID (will receive all data)",
                },
            },
            "required": ["sourceCustomerId", "targetCustomerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.linear.app/graphql"
        
        body = {
            "query": """
                mutation CustomerMerge($sourceCustomerId: String!, $targetCustomerId: String!) {
                  customerMerge(sourceCustomerId: $sourceCustomerId, targetCustomerId: $targetCustomerId) {
                    success
                    customer {
                      id
                      name
                      domains
                      externalIds
                      logoUrl
                      approximateNeedCount
                      createdAt
                      archivedAt
                    }
                  }
                }
            """,
            "variables": {
                "sourceCustomerId": parameters["sourceCustomerId"],
                "targetCustomerId": parameters["targetCustomerId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    resp_data = response.json()
                except ValueError:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if resp_data.get("errors"):
                    error_msg = "Failed to merge customers"
                    if isinstance(resp_data["errors"], list) and resp_data["errors"]:
                        error_msg = resp_data["errors"][0].get("message", error_msg)
                    return ToolResult(success=False, output="{}", error=error_msg)
                
                if "data" not in resp_data or "customerMerge" not in resp_data["data"]:
                    return ToolResult(success=False, output="", error="Unexpected response structure")
                
                result = resp_data["data"]["customerMerge"]
                output_data = {"customer": result.get("customer", {})}
                output_str = json.dumps(output_data)
                
                return ToolResult(
                    success=result.get("success", False),
                    output=output_str,
                    data=output_data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")