from typing import Any, Dict
from redis.asyncio import Redis
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisTtlTool(BaseTool):
    name = "redis_ttl"
    description = "Get the remaining time to live (in seconds) of a key in Redis."
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
                    "description": "The key to check TTL for",
                },
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            url = parameters["url"]
            key = parameters["key"]
            async with Redis.from_url(url, timeout=30.0) as client:
                ttl = await client.ttl(key)
            return ToolResult(
                success=True,
                output=str(ttl),
                data={
                    "key": key,
                    "ttl": ttl,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")