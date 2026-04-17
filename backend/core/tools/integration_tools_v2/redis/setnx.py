from typing import Any, Dict
import json
from redis.asyncio import Redis
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisSetnxTool(BaseTool):
    name = "Redis SETNX"
    description = "Set the value of a key in Redis only if the key does not already exist."
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
                    "description": "The key to set",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store",
                },
            },
            "required": ["url", "key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url: str = parameters["url"]
        key: str = parameters["key"]
        value: str = parameters["value"]

        try:
            redis_client = Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=30.0,
                socket_timeout=30.0,
            )
            result = await redis_client.setnx(key, value)
            await redis_client.aclose()
            was_set = result == 1
            output_data: Dict[str, Any] = {
                "key": key,
                "wasSet": was_set,
            }
            return ToolResult(
                success=True,
                output=json.dumps(output_data),
                data=output_data,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Redis error: {str(e)}",
            )