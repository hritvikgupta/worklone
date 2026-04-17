from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HexCancelRunTool(BaseTool):
    name = "hex_cancel_run"
    description = "Cancel an active Hex project run."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HEX_API_KEY",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hex",
            context=context,
            context_token_keys=("HEX_API_KEY",),
            env_token_keys=("HEX_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "The UUID of the Hex project",
                },
                "runId": {
                    "type": "string",
                    "description": "The UUID of the run to cancel",
                },
            },
            "required": ["projectId", "runId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Hex API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters["projectId"]
        run_id = parameters["runId"]
        url = f"https://app.hex.tech/api/v1/projects/{project_id}/runs/{run_id}"
        
        data = {
            "success": False,
            "projectId": project_id,
            "runId": run_id,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if 200 <= response.status_code < 300:
                    data["success"] = True
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("message", "Failed to cancel run")
                    except:
                        error_msg = response.text or "Failed to cancel run"
                    return ToolResult(success=False, output="", data=data, error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", data=data, error=f"API error: {str(e)}")