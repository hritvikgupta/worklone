from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListCustomerRequestsTool(BaseTool):
    name = "linear_list_customer_requests"
    description = "List all customer requests (needs) in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
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
                    "description": "Number of customer requests to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived customer requests (default: false)",
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
        
        query = """
        query ListCustomerNeeds($first: Int, $after: String, $includeArchived: Boolean) {
          customerNeeds(first: $first, after: $after, includeArchived: $includeArchived) {
            nodes {
              id
              body
              priority
              createdAt
              updatedAt
              archivedAt
              customer {
                id
                name
              }
              issue {
                id
                title
              }
              project {
                id
                name
              }
              creator {
                id
                name
              }
              url
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        variables = {
            "first": int(parameters.get("first", 50)),
            "includeArchived": parameters.get("includeArchived", False),
        }
        after = parameters.get("after")
        if after:
            variables["after"] = str(after).strip()
        
        body = {
            "query": query,
            "variables": variables,
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = "Failed to list customer requests"
                    if isinstance(errors, list) and errors:
                        first_error = errors[0]
                        if isinstance(first_error, dict):
                            error_msg = first_error.get("message", error_msg)
                    return ToolResult(success=False, output="", error=error_msg)
                    
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")