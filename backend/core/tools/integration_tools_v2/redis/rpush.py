from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisRPushTool(BaseTool):
    name = "redis_rpush"
    description = "Append a value to the end of a list stored at a key in Redis."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Redis connection URL (e.g. redis://user:password@host:port)",
                },
                "key": {
                    "type": "string",
                    "description": "The list key",
                },
                "value": {
                    "type": "string",
                    "description": "The value to append",
                },
            },
            "required": ["url", "key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "Content-Type": "application/json",
        }
        url = "/api/tools/redis/execute"
        body = {
            "url": parameters["url"],
            "command": "RPUSH",
            "args": [parameters["key"], parameters["value"]],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    output_dict = {
                        "key": parameters["key"],
                        "length": data.get("result", 0),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_dict),
                        data=output_dict,
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", "Failed to push to list in Redis")
                    except:
                        error_msg = response.text or "Failed to push to list in Redis"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")