from typing import Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis

class RedisGetTool(BaseTool):
    name = "redis_get"
    description = "Get the value of a key from Redis."
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
                    "description": "The key to retrieve",
                },
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url = parameters["url"]
        key = parameters["key"]

        try:
            async with Redis.from_url(url, decode_responses=True) as client:
                value = await client.get(key)

            data = {
                "key": key,
                "value": value,
            }
            output = value

            return ToolResult(success=True, output=output, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")