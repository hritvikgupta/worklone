from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HexRunProjectTool(BaseTool):
    name = "hex_run_project"
    description = "Execute a published Hex project. Optionally pass input parameters and control caching behavior."
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
            context_token_keys=("hex_api_key",),
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
                    "description": "The UUID of the Hex project to run",
                },
                "inputParams": {
                    "type": "object",
                    "description": "JSON object of input parameters for the project (e.g., {\"date\": \"2024-01-01\"})",
                    "additionalProperties": True,
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters["projectId"]
        url = f"https://app.hex.tech/api/v1/projects/{project_id}/runs"
        
        body: Dict[str, Any] = {}
        input_params = parameters.get("inputParams")
        if input_params:
            if isinstance(input_params, str):
                body["inputParams"] = json.loads(input_params)
            else:
                body["inputParams"] = input_params
        for key in ["dryRun", "updateCache", "updatePublishedResults", "useCachedSqlResults"]:
            value = parameters.get(key)
            if value is not None:
                body[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")