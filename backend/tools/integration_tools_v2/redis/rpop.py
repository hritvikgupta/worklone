from typing import Dict
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis
from redis.exceptions import RedisError

class RedisRPopTool(BaseTool):
    name = "redis_rpop"
    description = "Remove and return the last element of a list stored at a key in Redis."
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
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url = parameters["url"]
        key = parameters["key"]

        try:
            async with Redis.from_url(url) as r:
                value_bytes = await r.rpop(key)
                value = value_bytes.decode("utf-8") if value_bytes else None

            output_data = {
                "key": key,
                "value": value,
            }
            return ToolResult(success=True, output=str(output_data), data=output_data)

        except RedisError as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Unexpected error: {str(e)}")