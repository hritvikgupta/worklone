from typing import Any, Dict
import json
import redis.asyncio as redis
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisIncrbyTool(BaseTool):
    name = "redis_incrby"
    description = "Increment the integer value of a key by a given amount in Redis."
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
                    "description": "The key to increment",
                },
                "increment": {
                    "type": "number",
                    "description": "Amount to increment by (negative to decrement)",
                },
            },
            "required": ["url", "key", "increment"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            client = redis.from_url(parameters["url"])
            async with client:
                value = await client.incrby(parameters["key"], parameters["increment"])
            result_data = {
                "key": parameters["key"],
                "value": value,
            }
            return ToolResult(
                success=True,
                output=json.dumps(result_data),
                data=result_data,
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")