from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUnarchiveIssueTool(BaseTool):
    name = "linear_unarchive_issue"
    description = "Unarchive (restore) an archived issue in Linear"
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
                    "description": "Linear issue ID to unarchive",
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
        
        url = "https://api.linear.app/graphql"
        
        json_body = {
            "query": """
                mutation UnarchiveIssue($id: String!) {
                  issueUnarchive(id: $id) {
                    success
                    entity {
                      id
                    }
                  }
                }
            """,
            "variables": {
                "id": parameters["issueId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                    
                    if data.get("errors"):
                        errors = data["errors"]
                        error_msg = errors[0].get("message", "Failed to unarchive issue") if isinstance(errors, list) and errors else "Failed to unarchive issue"
                        return ToolResult(success=False, output="{}", error=error_msg)
                    
                    result = data.get("data", {}).get("issueUnarchive", {})
                    success = result.get("success", False)
                    issue_id = result.get("entity", {}).get("id")
                    output_data = {
                        "success": success,
                        "issueId": issue_id,
                    }
                    output_str = str(output_data)
                    return ToolResult(success=success, output=output_str, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")