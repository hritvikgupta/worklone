from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListAttachmentsTool(BaseTool):
    name = "linear_list_attachments"
    description = "List all attachments on an issue in Linear"
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
                "issueId": {
                    "type": "string",
                    "description": "Issue ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of attachments to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["issueId"],
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
        query ListAttachments($issueId: String!, $first: Int, $after: String) {
          issue(id: $issueId) {
            attachments(first: $first, after: $after) {
              nodes {
                id
                title
                subtitle
                url
                createdAt
                updatedAt
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        
        variables: Dict[str, Any] = {
            "issueId": parameters["issueId"],
        }
        first = parameters.get("first")
        variables["first"] = int(first) if first is not None else 50
        after = parameters.get("after")
        if after is not None and str(after).strip():
            variables["after"] = str(after).strip()
        
        body = {
            "query": query,
            "variables": variables,
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list attachments") if data["errors"] else "Failed to list attachments"
                    return ToolResult(success=False, output="", error=error_msg)
                
                issue_data = data.get("data", {}).get("issue")
                if not issue_data:
                    return ToolResult(success=False, output="", error="Issue not found")
                
                attachments_data = issue_data["attachments"]
                output_data = {
                    "attachments": attachments_data["nodes"],
                    "pageInfo": {
                        "hasNextPage": attachments_data["pageInfo"]["hasNextPage"],
                        "endCursor": attachments_data["pageInfo"]["endCursor"],
                    },
                }
                output_str = json.dumps(output_data)
                
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")