from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListNotificationsTool(BaseTool):
    name = "linear_list_notifications"
    description = "List notifications for the current user in Linear"
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
                    "description": "Number of notifications to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
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
        
        variables = {
            "first": int(parameters.get("first", 50)),
        }
        after = parameters.get("after", "").strip()
        if after:
            variables["after"] = after
        
        query = """
        query ListNotifications($first: Int, $after: String) {
          notifications(first: $first, after: $after) {
            nodes {
              id
              type
              createdAt
              readAt
              ... on IssueNotification {
                issue {
                  id
                  title
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        body = {
            "query": query,
            "variables": variables,
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list notifications")
                    return ToolResult(success=False, output="", error=error_msg)
                
                notifications_data = data.get("data", {}).get("notifications", {})
                output_dict = {
                    "notifications": notifications_data.get("nodes", []),
                    "pageInfo": {
                        "hasNextPage": notifications_data.get("pageInfo", {}).get("hasNextPage"),
                        "endCursor": notifications_data.get("pageInfo", {}).get("endCursor"),
                    },
                }
                output_str = json.dumps(output_dict)
                
                return ToolResult(success=True, output=output_str, data=output_dict)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")