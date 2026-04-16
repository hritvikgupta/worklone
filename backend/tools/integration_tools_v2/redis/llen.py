from typing import Any, Dict
import json
from redis.asyncio import Redis
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisLLenTool(BaseTool):
    name = "redis_llen"
    description = "Get the length of a list stored at a key in Redis."
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
        try:
            url = parameters["url"]
            key = parameters["key"]
            async with Redis.from_url(
                url,
                socket_connect_timeout=30.0,
                socket_timeout=30.0,
            ) as client:
                length = await client.llen(key)
            data = {
                "key": key,
                "length": length,
            }
            output = json.dumps(data)
            return ToolResult(success=True, output=output, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")