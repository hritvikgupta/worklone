from typing import Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis

class RedisHSetTool(BaseTool):
    name = "redis_hset"
    description = "Set a field in a hash stored at a key in Redis."
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
                    "description": "The hash key",
                },
                "field": {
                    "type": "string",
                    "description": "The field name within the hash",
                },
                "value": {
                    "type": "string",
                    "description": "The value to set for the field",
                },
            },
            "required": ["url", "key", "field", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            redis_client = Redis.from_url(parameters["url"])
            result = await redis_client.hset(
                parameters["key"],
                parameters["field"],
                parameters["value"],
            )
            await redis_client.aclose()
            return ToolResult(
                success=True,
                output=str(result),
                data={
                    "key": parameters["key"],
                    "field": parameters["field"],
                    "result": result,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")