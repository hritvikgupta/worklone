from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HexGetProjectRunsTool(BaseTool):
    name = "hex_get_project_runs"
    description = "Retrieve API-triggered runs for a Hex project with optional filtering by status and pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
            context_token_keys=("apiKey",),
            env_token_keys=("HEX_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Hex API token (Personal or Workspace)",
                },
                "projectId": {
                    "type": "string",
                    "description": "The UUID of the Hex project",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of runs to return (1-100, default: 25)",
                },
                "offset": {
                    "type": "number",
                    "description": "Offset for paginated results (default: 0)",
                },
                "statusFilter": {
                    "type": "string",
                    "description": "Filter by run status: PENDING, RUNNING, ERRORED, COMPLETED, KILLED, UNABLE_TO_ALLOCATE_KERNEL",
                },
            },
            "required": ["apiKey", "projectId"],
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
        
        params_dict = {
            "limit": parameters.get("limit"),
            "offset": parameters.get("offset"),
            "statusFilter": parameters.get("statusFilter"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    runs = data if isinstance(data, list) else data.get("runs", [])
                    mapped_runs = []
                    for r in runs:
                        mapped_runs.append({
                            "projectId": r.get("projectId"),
                            "runId": r.get("runId"),
                            "runUrl": r.get("runUrl"),
                            "status": r.get("status"),
                            "startTime": r.get("startTime"),
                            "endTime": r.get("endTime"),
                            "elapsedTime": r.get("elapsedTime"),
                            "traceId": r.get("traceId"),
                            "projectVersion": r.get("projectVersion"),
                        })
                    output_data = {
                        "runs": mapped_runs,
                        "total": len(mapped_runs),
                        "traceId": data.get("traceId"),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")