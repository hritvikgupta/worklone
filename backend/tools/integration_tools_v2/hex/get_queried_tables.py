from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult

class HexGetQueriedTablesTool(BaseTool):
    name = "hex_get_queried_tables"
    description = "Return the warehouse tables queried by a Hex project, including data connection and table names."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
                    "description": "Maximum number of tables to return (1-100)",
                },
            },
            "required": ["apiKey", "projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters["apiKey"]
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Hex API key not configured.")

        project_id = parameters["projectId"]
        limit = parameters.get("limit")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = "https://app.hex.tech/api/v1/projects/queriedTables"
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url.format(project_id=project_id),
                    headers=headers,
                    params=params,
                )

                if response.status_code in [200, 201, 204]:
                    resp_data = response.json()
                    tables_raw = (
                        resp_data
                        if isinstance(resp_data, list)
                        else (resp_data.get("values") if isinstance(resp_data, dict) else [])
                    )
                    tables = [
                        {
                            "dataConnectionId": t.get("dataConnectionId"),
                            "dataConnectionName": t.get("dataConnectionName"),
                            "tableName": t.get("tableName"),
                        }
                        for t in tables_raw
                    ]
                    result = {
                        "tables": tables,
                        "total": len(tables),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(result),
                        data=result,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=response.text,
                    )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"API error: {str(e)}",
            )