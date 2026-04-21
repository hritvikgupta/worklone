from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListCustomersTool(BaseTool):
    name = "linear_list_customers"
    description = "List all customers in Linear"
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
                "first": {
                    "type": "number",
                    "description": "Number of customers to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived customers (default: false)",
                },
            },
            "required": [],
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
        
        query = """
        query ListCustomers($first: Int, $after: String, $includeArchived: Boolean) {
          customers(first: $first, after: $after, includeArchived: $includeArchived) {
            nodes {
              id
              name
              domains
              externalIds
              logoUrl
              slugId
              approximateNeedCount
              revenue
              size
              createdAt
              updatedAt
              archivedAt
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        variables: Dict[str, Any] = {
            "includeArchived": parameters.get("includeArchived", False),
        }
        first_val = parameters.get("first")
        variables["first"] = int(first_val) if first_val is not None else 50
        
        after_val = parameters.get("after")
        if after_val:
            variables["after"] = str(after_val).strip()
        else:
            variables["after"] = None
        
        body = {
            "query": query,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if data.get("errors"):
                        error_msg = data["errors"][0].get("message", "Failed to list customers")
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    customers_data = data.get("data", {}).get("customers", {})
                    output_dict = {
                        "customers": customers_data.get("nodes", []),
                        "pageInfo": {
                            "hasNextPage": customers_data.get("pageInfo", {}).get("hasNextPage", False),
                            "endCursor": customers_data.get("pageInfo", {}).get("endCursor"),
                        },
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_dict, indent=2),
                        data=output_dict,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")