from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearArchiveLabelTool(BaseTool):
    name = "linear_archive_label"
    description = "Archive a label in Linear"
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
                "labelId": {
                    "type": "string",
                    "description": "Label ID to archive",
                },
            },
            "required": ["labelId"],
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
                mutation ArchiveLabel($id: String!) {
                  issueLabelArchive(id: $id) {
                    success
                  }
                }
            """,
            "variables": {
                "id": parameters["labelId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                
                response_data = response.json()
                
                if "errors" in response_data and response_data["errors"]:
                    error_msg = (
                        response_data["errors"][0].get("message", "Unknown GraphQL error")
                        if response_data["errors"]
                        else "Failed to archive label"
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response_data.get("data", {})
                archive_result = data.get("issueLabelArchive", {})
                success = archive_result.get("success", False)
                
                output_data = {
                    "success": success,
                    "labelId": parameters.get("labelId", ""),
                }
                
                return ToolResult(
                    success=success,
                    output=response.text,
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")