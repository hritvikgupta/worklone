from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearAddLabelToIssueTool(BaseTool):
    name = "Linear Add Label to Issue"
    description = "Add a label to an issue in Linear"
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
                "issueId": {
                    "type": "string",
                    "description": "Linear issue ID",
                },
                "labelId": {
                    "type": "string",
                    "description": "Label ID to add to the issue",
                },
            },
            "required": ["issueId", "labelId"],
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
                mutation AddLabelToIssue($issueId: String!, $labelId: String!) {
                  issueAddLabel(id: $issueId, labelId: $labelId) {
                    success
                    issue {
                      id
                    }
                  }
                }
            """,
            "variables": {
                "issueId": parameters["issueId"],
                "labelId": parameters["labelId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to add label to issue")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("issueAddLabel", {})
                success = result.get("success", False)
                issue_id = result.get("issue", {}).get("id", "") if result.get("issue") else ""
                output_data = {
                    "success": success,
                    "issueId": issue_id,
                }
                return ToolResult(success=success, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")